from types import SimpleNamespace
from unittest import TestCase, mock

import pandas as pd

from snipergw.model import EventConfig, PlanConfig
from snipergw.run import run_snipergw


class TestRunSnipergw(TestCase):
    """
    Test the run_snipergw orchestration function, with the skymap/gwemopt/
    submission calls mocked out.
    """

    def setUp(self):
        self.event = EventConfig(event="S190425z", rev=2)
        self.schedule = pd.DataFrame({"field": [1], "filter": ["g"], "tobs": [1.0]})

    @mock.patch("snipergw.run.submit_too_winter")
    @mock.patch("snipergw.run.submit_too_ztf")
    @mock.patch("snipergw.run.run_gwemopt")
    @mock.patch("snipergw.run.Skymap")
    def test_no_submit_or_delete_does_not_call_submission(
        self, mock_skymap, mock_run_gwemopt, mock_submit_ztf, mock_submit_winter
    ):
        mock_run_gwemopt.return_value = self.schedule
        plan_config = PlanConfig(telescope="ZTF")

        run_snipergw(event=self.event, plan_config=plan_config)

        mock_skymap.assert_called_once_with(event_config=self.event)
        mock_run_gwemopt.assert_called_once()
        mock_submit_ztf.assert_not_called()
        mock_submit_winter.assert_not_called()

    @mock.patch("snipergw.run.submit_too_winter")
    @mock.patch("snipergw.run.submit_too_ztf")
    @mock.patch("snipergw.run.run_gwemopt")
    @mock.patch("snipergw.run.Skymap")
    def test_submit_ztf_dispatches_to_ztf(
        self, mock_skymap, mock_run_gwemopt, mock_submit_ztf, mock_submit_winter
    ):
        mock_run_gwemopt.return_value = self.schedule
        plan_config = PlanConfig(telescope="ZTF")

        run_snipergw(event=self.event, plan_config=plan_config, submit=True)

        mock_submit_ztf.assert_called_once_with(
            self.schedule,
            event_name=self.event.event,
            plan_config=plan_config,
            submit=True,
            delete=False,
        )
        mock_submit_winter.assert_not_called()

    @mock.patch("snipergw.run.submit_too_winter")
    @mock.patch("snipergw.run.submit_too_ztf")
    @mock.patch("snipergw.run.run_gwemopt")
    @mock.patch("snipergw.run.Skymap")
    def test_delete_winter_dispatches_to_winter(
        self, mock_skymap, mock_run_gwemopt, mock_submit_ztf, mock_submit_winter
    ):
        mock_run_gwemopt.return_value = self.schedule
        plan_config = PlanConfig(telescope="WINTER")

        run_snipergw(event=self.event, plan_config=plan_config, delete=True)

        mock_submit_winter.assert_called_once_with(
            self.schedule,
            event_name=self.event.event,
            plan_config=plan_config,
            submit=False,
            delete=True,
        )
        mock_submit_ztf.assert_not_called()

    @mock.patch("snipergw.run.submit_too_winter")
    @mock.patch("snipergw.run.submit_too_ztf")
    @mock.patch("snipergw.run.run_gwemopt")
    @mock.patch("snipergw.run.Skymap")
    def test_unsupported_telescope_raises(
        self, mock_skymap, mock_run_gwemopt, mock_submit_ztf, mock_submit_winter
    ):
        mock_run_gwemopt.return_value = self.schedule
        # DECam can't be constructed via PlanConfig (see test_model.py), so
        # use a stand-in with the attribute run_snipergw actually reads.
        plan_config = SimpleNamespace(telescope="DECam")

        with self.assertRaises(NotImplementedError):
            run_snipergw(event=self.event, plan_config=plan_config, submit=True)

        mock_submit_ztf.assert_not_called()
        mock_submit_winter.assert_not_called()
