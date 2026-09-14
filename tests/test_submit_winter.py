from unittest import TestCase, mock

import pandas as pd
from astropy.time import Time

import snipergw.submit.winter as winter_module
from snipergw.submit.winter import MAX_EXPOSURE_TIME, MIN_DITHER, submit_too_winter


class TestSubmitTooWinter(TestCase):
    """
    Test submit_too_winter, with the module-level `winter` WinterAPI client
    mocked out so no real network/credential calls are made.
    """

    def setUp(self) -> None:
        """
        :return: None
        """
        now_mjd = Time.now().mjd
        self.schedule: pd.DataFrame = pd.DataFrame(
            {
                "field": [100, 200],
                "filter": ["J", "J"],
                "tobs": [now_mjd + 0.1, now_mjd + 0.3],
            }
        )
        self.plan_config: mock.Mock = mock.Mock(exposuretime=450.0)

    def test_delete_not_implemented(self) -> None:
        """
        delete=True should raise NotImplementedError before ever touching
        the module-level `winter` client

        :return: None
        """
        with mock.patch.object(winter_module, "winter") as mock_winter:
            with self.assertRaises(NotImplementedError):
                submit_too_winter(
                    self.schedule,
                    event_name="S190425z",
                    plan_config=self.plan_config,
                    delete=True,
                )
            mock_winter.get_user.assert_not_called()

    @mock.patch.dict(
        "os.environ",
        {"WINTER_PROGRAM_NAME": "2020A000", "WINTER_PROGRAM_KEY": "secret"},
    )
    def test_submit_builds_expected_too_list_and_submits(self) -> None:
        """
        submit_too_winter should build one WinterFieldToO per schedule
        row, with the expected target name, dithers, and exposure time,
        and pass them to winter.submit_too

        :return: None
        """
        with mock.patch.object(winter_module, "winter") as mock_winter:
            mock_winter.get_user.return_value = "test-user"
            mock_winter.get_programs.return_value = ["2020A000"]
            mock_winter.submit_too.return_value = ("ok", "schedule")

            submit_too_winter(
                self.schedule,
                event_name="S190425z",
                plan_config=self.plan_config,
                submit=True,
            )

            mock_winter.add_program.assert_not_called()
            mock_winter.submit_too.assert_called_once()

            _, kwargs = mock_winter.submit_too.call_args
            self.assertEqual(kwargs["program_name"], "2020A000")
            self.assertTrue(kwargs["submit_trigger"])
            too_list = kwargs["data"]
            self.assertEqual(len(too_list), len(self.schedule))

            expected_n_dithers = int(
                max(self.plan_config.exposuretime / MAX_EXPOSURE_TIME, MIN_DITHER)
            )
            for too, (_, row) in zip(too_list, self.schedule.iterrows()):
                self.assertEqual(too.target_name, f"S190425z_{row['field']}")
                self.assertEqual(too.field_id, row["field"])
                self.assertEqual(too.filters, [row["filter"]])
                self.assertEqual(too.n_dither, expected_n_dithers)
                self.assertEqual(too.total_exposure_time, self.plan_config.exposuretime)

    @mock.patch.dict(
        "os.environ",
        {"WINTER_PROGRAM_NAME": "2020A000", "WINTER_PROGRAM_KEY": "secret"},
    )
    def test_submit_adds_program_when_missing(self) -> None:
        """
        If WINTER_PROGRAM_NAME isn't already in winter.get_programs(), it
        should be registered via winter.add_program

        :return: None
        """
        with mock.patch.object(winter_module, "winter") as mock_winter:
            mock_winter.get_user.return_value = "test-user"
            mock_winter.get_programs.return_value = []
            mock_winter.submit_too.return_value = ("ok", "schedule")

            submit_too_winter(
                self.schedule,
                event_name="S190425z",
                plan_config=self.plan_config,
                submit=False,
            )

            mock_winter.add_program.assert_called_once_with("2020A000", "secret")

    @mock.patch.dict(
        "os.environ",
        {"WINTER_PROGRAM_NAME": "2020A000", "WINTER_PROGRAM_KEY": "secret"},
    )
    def test_submit_adds_user_details_when_missing(self) -> None:
        """
        If winter.get_user() raises KeyError (no stored credentials),
        winter.add_user_details should be called to set them up

        :return: None
        """
        with mock.patch.object(winter_module, "winter") as mock_winter:
            mock_winter.get_user.side_effect = KeyError("no user")
            mock_winter.get_programs.return_value = ["2020A000"]
            mock_winter.submit_too.return_value = ("ok", "schedule")

            submit_too_winter(
                self.schedule,
                event_name="S190425z",
                plan_config=self.plan_config,
                submit=False,
            )

            mock_winter.add_user_details.assert_called_once_with(overwrite=True)
