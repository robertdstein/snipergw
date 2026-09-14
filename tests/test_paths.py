import importlib
import os
from pathlib import Path
from unittest import TestCase, mock

import snipergw.paths as paths


class TestPaths(TestCase):
    """
    Test the paths module
    """

    def tearDown(self):
        # Make sure other tests always see the module reloaded with a clean
        # environment, regardless of what this test did to os.environ.
        importlib.reload(paths)

    def test_default_base_output_dir(self):
        """
        With SNIPERGW_DIR unset, base_output_dir should default to
        ~/Data/snipergw/
        """
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("SNIPERGW_DIR", None)
            importlib.reload(paths)

        self.assertEqual(paths.base_output_dir, Path.home().joinpath("Data/snipergw/"))
        self.assertIsInstance(paths.base_output_dir, Path)

    def test_base_output_dir_from_env(self):
        """
        With SNIPERGW_DIR set, base_output_dir should be that path,
        converted from a string to a Path
        """
        with mock.patch.dict(os.environ, {"SNIPERGW_DIR": "/tmp/some/snipergw/dir"}):
            importlib.reload(paths)

        self.assertEqual(paths.base_output_dir, Path("/tmp/some/snipergw/dir"))
        self.assertIsInstance(paths.base_output_dir, Path)

    def test_gwemopt_dir(self):
        """
        gwemopt_dir should point at a "gwemopt" subdirectory
        """
        self.assertEqual(paths.gwemopt_dir.name, "gwemopt")
