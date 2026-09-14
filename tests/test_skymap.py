import tempfile
from pathlib import Path
from unittest import TestCase, mock

from snipergw.model import EventConfig
from snipergw.skymap import Skymap


def _bare_skymap(base_skymap_dir: Path) -> Skymap:
    """
    Build a Skymap instance without running __init__ (which downloads/reads
    a real skymap), so individual helper methods can be tested in isolation.

    :param base_skymap_dir: Directory to use as the instance's
        base_skymap_dir
    :return: Skymap instance with only base_skymap_dir set
    """
    skymap = Skymap.__new__(Skymap)
    skymap.base_skymap_dir = base_skymap_dir
    return skymap


class TestParseFitsFile(TestCase):
    """
    Test Skymap.parse_fits_file
    """

    def setUp(self) -> None:
        """
        :return: None
        """
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp_dir.cleanup)
        self.base_skymap_dir: Path = Path(self.tmp_dir.name)
        self.skymap: Skymap = _bare_skymap(self.base_skymap_dir)

    def test_existing_local_file_is_reused(self) -> None:
        """
        A file already present in base_skymap_dir should be reused as-is,
        without attempting a download

        :return: None
        """
        existing = self.base_skymap_dir.joinpath("event.fits")
        existing.touch()

        with mock.patch("snipergw.skymap.wget.download") as mock_download:
            skymap_path, event_name = self.skymap.parse_fits_file("event.fits")

        mock_download.assert_not_called()
        self.assertEqual(skymap_path, existing)
        self.assertEqual(event_name, "event.fits")

    def test_https_url_is_downloaded(self) -> None:
        """
        An https:// event should be downloaded into base_skymap_dir

        :return: None
        """
        url = "https://example.com/dir/remote_event.fits"

        with mock.patch("snipergw.skymap.wget.download") as mock_download:
            skymap_path, event_name = self.skymap.parse_fits_file(url)

        mock_download.assert_called_once()
        self.assertEqual(skymap_path.name, "remote_event.fits")
        self.assertEqual(event_name, "remote_event.fits")

    def test_unrecognised_path_raises(self) -> None:
        """
        A path that's neither an existing local file nor an https:// URL
        should raise FileNotFoundError

        :return: None
        """
        with self.assertRaises(FileNotFoundError):
            self.skymap.parse_fits_file("not_a_real_local_or_remote_file.fits")


class TestSkymapInit(TestCase):
    """
    Test the event-type dispatch branching in Skymap.__init__, with the
    (network-heavy) download/read methods mocked out.
    """

    def setUp(self) -> None:
        """
        :return: None
        """
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp_dir.cleanup)
        self.output_dir: Path = Path(self.tmp_dir.name)
        # read_map() always runs at the end of __init__ and needs a real
        # fits file, so it's mocked out in every dispatch test below.
        self.read_map_patch = mock.patch.object(Skymap, "read_map", return_value=None)
        self.read_map_patch.start()
        self.addCleanup(self.read_map_patch.stop)

    def test_unrecognised_event_raises(self) -> None:
        """
        An event string matching none of the fits/GW/GRB patterns should
        raise

        :return: None
        """
        event_config = EventConfig(
            event="not-a-known-format", output_dir=self.output_dir
        )
        with self.assertRaises(Exception) as ctx:
            Skymap(event_config=event_config)

        self.assertIn("not recognised", str(ctx.exception))

    def test_fits_event_dispatches_to_parse_fits_file(self) -> None:
        """
        An event name containing ".fit" should dispatch to parse_fits_file

        :return: None
        """
        event_config = EventConfig(event="local.fits", output_dir=self.output_dir)
        with mock.patch.object(
            Skymap, "parse_fits_file", return_value=("path", "local.fits")
        ) as mock_parse:
            skymap = Skymap(event_config=event_config)

        mock_parse.assert_called_once_with("local.fits")
        self.assertEqual(skymap.event_name, "local.fits")
        self.assertFalse(skymap.is_3d)

    def test_none_event_dispatches_to_gw_skymap(self) -> None:
        """
        event=None should dispatch to get_gw_skymap and set is_3d=True

        :return: None
        """
        event_config = EventConfig(event=None, rev=3, output_dir=self.output_dir)
        with mock.patch.object(
            Skymap, "get_gw_skymap", return_value=("path", "S000000a")
        ) as mock_get_gw:
            skymap = Skymap(event_config=event_config)

        mock_get_gw.assert_called_once_with(event_name=None, rev=3)
        self.assertEqual(skymap.event_name, "S000000a")
        self.assertTrue(skymap.is_3d)

    def test_gw_like_event_dispatches_to_gw_skymap(self) -> None:
        """
        An event name containing "S"/"gw"/"GW" should dispatch to
        get_gw_skymap and set is_3d=True

        :return: None
        """
        event_config = EventConfig(event="S190425z", rev=2, output_dir=self.output_dir)
        with mock.patch.object(
            Skymap, "get_gw_skymap", return_value=("path", "S190425z")
        ) as mock_get_gw:
            skymap = Skymap(event_config=event_config)

        mock_get_gw.assert_called_once_with(event_name="S190425z", rev=2)
        self.assertEqual(skymap.event_name, "S190425z")
        self.assertTrue(skymap.is_3d)

    def test_grb_event_dispatches_to_grb_skymap(self) -> None:
        """
        An event name containing "GRB" should dispatch to get_grb_skymap
        and leave is_3d=False

        :return: None
        """
        event_config = EventConfig(event="GRB210729A", output_dir=self.output_dir)
        with mock.patch.object(
            Skymap, "get_grb_skymap", return_value=("path", "GRB210729A")
        ) as mock_get_grb:
            skymap = Skymap(event_config=event_config)

        mock_get_grb.assert_called_once_with(event_name="GRB210729A")
        self.assertEqual(skymap.event_name, "GRB210729A")
        self.assertFalse(skymap.is_3d)


# Two GBM trigger folders on the same date, so get_grb_skymap's
# "found multiple events" branch is also exercised.
_OVERVIEW_HTML = """
<html><body>
<a href="bn210729000/">bn210729000/</a>
<a href="bn210729001/">bn210729001/</a>
</body></html>
"""

_EVENT_PAGE_HTML = """
<html><body>
<a href="other_file.fit">other_file.fit</a>
<a href="glg_healpix_all_bn210729000_v00.fit">glg_healpix_all_bn210729000_v00.fit</a>
</body></html>
"""


class TestGetGrbSkymap(TestCase):
    """
    Test Skymap.get_grb_skymap, with the HTTP calls to HEASARC mocked out
    using minimal realistic HTML fixtures (so the real lxml parsing/link
    matching logic is still exercised).
    """

    def setUp(self) -> None:
        """
        :return: None
        """
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp_dir.cleanup)
        self.skymap: Skymap = _bare_skymap(Path(self.tmp_dir.name))

    def _mock_responses(self) -> list[mock.Mock]:
        """
        Build the two fake requests.get responses get_grb_skymap consumes
        in order: the trigger-date overview page, then the event page.

        :return: [overview_response, event_response]
        """
        overview_response = mock.Mock(content=_OVERVIEW_HTML.encode())
        event_response = mock.Mock(content=_EVENT_PAGE_HTML.encode())
        return [overview_response, event_response]

    def test_downloads_when_not_already_saved(self) -> None:
        """
        When the matched healpix file isn't already saved locally, it
        should be downloaded from the resolved final_link

        :return: None
        """
        with (
            mock.patch(
                "snipergw.skymap.requests.get", side_effect=self._mock_responses()
            ),
            mock.patch("snipergw.skymap.wget.download") as mock_download,
        ):
            skymap_path, event_name = self.skymap.get_grb_skymap("grb210729a")

        mock_download.assert_called_once()
        self.assertEqual(event_name, "GRB210729A")
        self.assertEqual(skymap_path.name, "glg_healpix_all_bn210729000_v00.fit")

    def test_reuses_existing_local_file(self) -> None:
        """
        When the matched healpix file already exists locally, it should
        be reused without downloading

        :return: None
        """
        existing = Path(self.tmp_dir.name).joinpath(
            "glg_healpix_all_bn210729000_v00.fit"
        )
        existing.touch()

        with (
            mock.patch(
                "snipergw.skymap.requests.get", side_effect=self._mock_responses()
            ),
            mock.patch("snipergw.skymap.wget.download") as mock_download,
        ):
            skymap_path, _ = self.skymap.get_grb_skymap("GRB210729A")

        mock_download.assert_not_called()
        self.assertEqual(skymap_path, existing)

    def test_missing_event_name_raises(self) -> None:
        """
        get_grb_skymap requires an event name and should reject None

        :return: None
        """
        with self.assertRaises(ValueError):
            self.skymap.get_grb_skymap(None)
