from unittest import TestCase

from pydantic import ValidationError

from snipergw.model import EventConfig, PlanConfig, winter_default, ztf_default


class TestEventConfig(TestCase):
    """
    Test the EventConfig model
    """

    def test_defaults(self):
        """
        event/rev should both default to None
        """
        event = EventConfig()
        self.assertIsNone(event.event)
        self.assertIsNone(event.rev)


class TestPlanConfig(TestCase):
    """
    Test the PlanConfig model
    """

    def test_ztf_defaults(self):
        """
        ZTF telescope should fall back to ztf_default filters/exposuretime
        """
        plan_config = PlanConfig(telescope="ZTF")
        self.assertEqual(plan_config.filters, ztf_default.filters)
        self.assertEqual(plan_config.exposuretime, ztf_default.exposuretime)

    def test_winter_defaults(self):
        """
        WINTER telescope should fall back to winter_default filters/exposuretime
        """
        plan_config = PlanConfig(telescope="WINTER")
        self.assertEqual(plan_config.filters, winter_default.filters)
        self.assertEqual(plan_config.exposuretime, winter_default.exposuretime)

    def test_unknown_telescope_rejected(self):
        """
        A telescope not in all_telescopes should fail validation
        """
        with self.assertRaises(ValidationError):
            PlanConfig(telescope="not-a-telescope")

    def test_decam_always_rejected(self):
        """
        DECam is listed in all_telescopes, but set_default_filter's
        per-filter validation loop only special-cases ZTF/WINTER and
        otherwise always raises -- so DECam can never actually be
        constructed, even with explicit filters/exposuretime.
        """
        with self.assertRaises(ValidationError):
            PlanConfig(telescope="DECam")

        with self.assertRaises(ValidationError):
            PlanConfig(telescope="DECam", filters="g", exposuretime=100.0)

    def test_ztf_rejects_unknown_filter(self):
        """
        A filter outside ztf_default.all_filters should fail validation
        """
        with self.assertRaises((ValidationError, AssertionError)):
            PlanConfig(telescope="ZTF", filters="x")

    def test_winter_rejects_unknown_filter(self):
        """
        A filter outside winter_default.all_filters should fail validation
        """
        with self.assertRaises((ValidationError, AssertionError)):
            PlanConfig(telescope="WINTER", filters="x")
