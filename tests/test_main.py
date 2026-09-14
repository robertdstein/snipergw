import runpy
import sys
from unittest import TestCase, mock

import snipergw.run as run_module


class TestMain(TestCase):
    """
    Test the snipergw.__main__ CLI entry point: argument parsing and how it
    is wired into run_snipergw (which is mocked out here).
    """

    def _run_main(self, argv: list[str]) -> mock.MagicMock:
        """
        Run snipergw.__main__ with the given CLI args and sys.argv[0],
        with run_snipergw mocked out, returning that mock for inspection.

        :param argv: CLI arguments to parse (excluding argv[0])
        :return: Mock replacing snipergw.run.run_snipergw, as called by
            __main__
        """
        with mock.patch.object(sys, "argv", ["snipergw"] + argv):
            with mock.patch.object(run_module, "run_snipergw") as mock_run:
                runpy.run_module("snipergw.__main__", run_name="__main__")
        return mock_run

    def test_default_args_call_run_snipergw(self) -> None:
        """
        Basic -e/-r args should build the expected EventConfig/PlanConfig
        and call run_snipergw once, with submit/delete left False

        :return: None
        """
        mock_run = self._run_main(["-e", "S190425z", "-r", "2"])

        mock_run.assert_called_once()
        _, kwargs = mock_run.call_args
        self.assertEqual(kwargs["event"].event, "S190425z")
        self.assertEqual(kwargs["event"].rev, 2)
        self.assertEqual(kwargs["plan_config"].telescope, "ZTF")
        self.assertFalse(kwargs["submit"])
        self.assertFalse(kwargs["delete"])

    def test_submit_and_delete_flags_passed_through(self) -> None:
        """
        The -s/-d flags should be passed through to run_snipergw as True

        :return: None
        """
        mock_run = self._run_main(["-e", "S190425z", "-s", "-d"])

        _, kwargs = mock_run.call_args
        self.assertTrue(kwargs["submit"])
        self.assertTrue(kwargs["delete"])

    def test_starttime_is_parsed_into_time_object(self) -> None:
        """
        The -st flag should be parsed from an isot string into a Time on
        plan_config.starttime

        :return: None
        """
        mock_run = self._run_main(["-e", "S190425z", "-st", "2020-01-01T00:00:00"])

        _, kwargs = mock_run.call_args
        self.assertEqual(kwargs["plan_config"].starttime.isot[:10], "2020-01-01")

    def test_extra_args_passed_as_gwemopt_args(self) -> None:
        """
        Unrecognised CLI args should be forwarded as gwemopt_args rather
        than raising an argparse error

        :return: None
        """
        mock_run = self._run_main(["-e", "S190425z", "--some-gwemopt-flag", "value"])

        _, kwargs = mock_run.call_args
        self.assertIn("--some-gwemopt-flag", kwargs["gwemopt_args"])
        self.assertIn("value", kwargs["gwemopt_args"])
