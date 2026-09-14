import json
import tempfile
from pathlib import Path
from unittest import TestCase, mock

import pandas as pd
from penquins import Kowalski
from planobs.api import APIError

import snipergw.submit.ztf as ztf


class TestKowalskiBearerPatch(TestCase):
    """
    Test the Kowalski.__init__ patch that adds the "Bearer " prefix the
    ztfpass server requires (the old Kowalski route sent the bare token).
    """

    def test_bearer_prefix_added_to_every_instance(self):
        """
        A single Kowalski instance's Authorization header should be
        rewritten from the bare token to "Bearer <token>"
        """

        def fake_original_init(self, *_args, **kwargs):
            token = kwargs.get("token")
            self.instances = {
                "default": {"token": token, "headers": {"Authorization": token}}
            }

        with mock.patch.object(ztf, "_original_kowalski_init", fake_original_init):
            kowalski = Kowalski(token="abc123")

        self.assertEqual(
            kowalski.instances["default"]["headers"]["Authorization"], "Bearer abc123"
        )

    def test_multiple_instances_all_patched(self):
        """
        Every instance in a multi-instance Kowalski client should get the
        "Bearer " prefix, not just the first
        """

        def fake_original_init(self, *_args, **_kwargs):
            self.instances = {
                "one": {"token": "tok1", "headers": {"Authorization": "tok1"}},
                "two": {"token": "tok2", "headers": {"Authorization": "tok2"}},
            }

        with mock.patch.object(ztf, "_original_kowalski_init", fake_original_init):
            kowalski = Kowalski()

        self.assertEqual(
            kowalski.instances["one"]["headers"]["Authorization"], "Bearer tok1"
        )
        self.assertEqual(
            kowalski.instances["two"]["headers"]["Authorization"], "Bearer tok2"
        )

    def test_missing_token_leaves_headers_untouched(self):
        """
        An instance with no token (e.g. username/password auth) shouldn't
        get an Authorization header added
        """

        def fake_original_init(self, *_args, **_kwargs):
            self.instances = {"default": {"token": None, "headers": {}}}

        with mock.patch.object(ztf, "_original_kowalski_init", fake_original_init):
            kowalski = Kowalski()

        self.assertNotIn("Authorization", kowalski.instances["default"]["headers"])


class TestSubmitTooZtf(TestCase):
    """
    Test submit_too_ztf with planobs.api.Queue mocked out, so no real
    network calls to the ZTF ToO server are made.
    """

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp_dir.cleanup)

        self.schedule = pd.DataFrame(
            {
                "field": [1728],
                "filter": ["g"],
                "texp": [300.0],
                "tobs": [58598.5],
            }
        )
        self.plan_config = mock.Mock(subprogram="EMGW")
        self.event_name = "S190425z"
        self.trigger_name = f"ToO_{self.plan_config.subprogram}_{self.event_name}"
        self.expected_name = f"{self.trigger_name}_0"

    def _patched_queue(self, mock_queue_cls):
        """
        Configure the mocked Queue class with a single-entry .queue dict,
        keyed the same way planobs.api.Queue keys it.
        """
        mock_queue = mock_queue_cls.return_value
        mock_queue.queue = {0: {"queue_name": self.expected_name}}
        return mock_queue

    @mock.patch("snipergw.submit.ztf.time.sleep")
    @mock.patch("snipergw.submit.ztf.base_output_dir")
    @mock.patch("snipergw.submit.ztf.Queue")
    def test_submit_writes_json_and_submits_queue(
        self, mock_queue_cls, mock_base_output_dir, mock_sleep
    ):
        """
        submit=True should add the trigger, submit the queue, write a json
        file per queue entry, and confirm the trigger landed in the queue
        """
        output_root = Path(self.tmp_dir.name)
        mock_base_output_dir.__truediv__ = lambda _self, other: output_root / other

        mock_queue = self._patched_queue(mock_queue_cls)
        mock_queue.get_too_queues.return_value = {
            "data": [{"queue_name": self.expected_name}]
        }
        mock_queue.delete_queue.side_effect = APIError("no pre-existing queue")

        ztf.submit_too_ztf(
            schedule=self.schedule,
            event_name=self.event_name,
            plan_config=self.plan_config,
            submit=True,
        )

        mock_queue.add_trigger_to_queue.assert_called_once()
        mock_queue.submit_queue.assert_called_once()
        mock_sleep.assert_called_once_with(5)

        json_path = (
            output_root / f"{self.event_name}/ZTF/json/{self.expected_name}.json"
        )
        self.assertTrue(json_path.exists())
        with json_path.open() as f:
            self.assertEqual(json.load(f), {"queue_name": self.expected_name})

    @mock.patch("snipergw.submit.ztf.time.sleep")
    @mock.patch("snipergw.submit.ztf.base_output_dir")
    @mock.patch("snipergw.submit.ztf.Queue")
    def test_submit_deletes_preexisting_queue_of_same_name(
        self, mock_queue_cls, mock_base_output_dir, mock_sleep
    ):
        """
        submit=True should delete any pre-existing queue of the same name
        (delete_queue succeeding, not raising APIError) before submitting
        """
        output_root = Path(self.tmp_dir.name)
        mock_base_output_dir.__truediv__ = lambda _self, other: output_root / other

        mock_queue = self._patched_queue(mock_queue_cls)
        mock_queue.get_too_queues.return_value = {
            "data": [{"queue_name": self.expected_name}]
        }
        # No exception this time: a pre-existing queue of the same name exists.
        mock_queue.delete_queue.return_value = None

        ztf.submit_too_ztf(
            schedule=self.schedule,
            event_name=self.event_name,
            plan_config=self.plan_config,
            submit=True,
        )

        mock_queue.delete_queue.assert_called_once()
        mock_queue.submit_queue.assert_called_once()

    @mock.patch("snipergw.submit.ztf.time.sleep")
    @mock.patch("snipergw.submit.ztf.base_output_dir")
    @mock.patch("snipergw.submit.ztf.Queue")
    def test_submit_raises_if_trigger_missing_from_queue(
        self, mock_queue_cls, mock_base_output_dir, mock_sleep
    ):
        """
        If the expected trigger name never shows up in the queue after
        submitting, submit_too_ztf should raise RuntimeError
        """
        output_root = Path(self.tmp_dir.name)
        mock_base_output_dir.__truediv__ = lambda _self, other: output_root / other

        mock_queue = self._patched_queue(mock_queue_cls)
        mock_queue.get_too_queues.return_value = {"data": []}
        mock_queue.delete_queue.side_effect = APIError("no pre-existing queue")

        with self.assertRaises(RuntimeError):
            ztf.submit_too_ztf(
                schedule=self.schedule,
                event_name=self.event_name,
                plan_config=self.plan_config,
                submit=True,
            )

    @mock.patch("snipergw.submit.ztf.base_output_dir")
    @mock.patch("snipergw.submit.ztf.Queue")
    def test_delete_removes_existing_trigger(
        self, mock_queue_cls, mock_base_output_dir
    ):
        """
        delete=True should delete the queue when the trigger is present
        """
        output_root = Path(self.tmp_dir.name)
        mock_base_output_dir.__truediv__ = lambda _self, other: output_root / other

        mock_queue = self._patched_queue(mock_queue_cls)
        mock_queue.get_too_queues.side_effect = [
            {"data": [{"queue_name": self.expected_name}]},
            {"data": []},
        ]

        ztf.submit_too_ztf(
            schedule=self.schedule,
            event_name=self.event_name,
            plan_config=self.plan_config,
            delete=True,
        )

        mock_queue.delete_queue.assert_called_once()

    @mock.patch("snipergw.submit.ztf.base_output_dir")
    @mock.patch("snipergw.submit.ztf.Queue")
    def test_delete_raises_if_trigger_not_in_queue(
        self, mock_queue_cls, mock_base_output_dir
    ):
        """
        delete=True should raise RuntimeError (and never call
        delete_queue) if the trigger isn't in the queue
        """
        output_root = Path(self.tmp_dir.name)
        mock_base_output_dir.__truediv__ = lambda _self, other: output_root / other

        mock_queue = self._patched_queue(mock_queue_cls)
        mock_queue.get_too_queues.return_value = {"data": []}

        with self.assertRaises(RuntimeError):
            ztf.submit_too_ztf(
                schedule=self.schedule,
                event_name=self.event_name,
                plan_config=self.plan_config,
                delete=True,
            )

        mock_queue.delete_queue.assert_not_called()
