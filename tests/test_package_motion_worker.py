import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

from tools.package_motion_worker import FILES, build


class MotionWorkerBundleTests(unittest.TestCase):
    def test_reproducible_bundle_runs_without_the_sdk_checkout(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = root / "worker.zip"
            second = root / "repeat.zip"
            self.assertEqual(build(first), build(second))

            install = root / "installed"
            with ZipFile(first) as archive:
                self.assertEqual(archive.namelist(), list(FILES))
                archive.extractall(install)
            result = subprocess.run(
                [sys.executable, "-E", "-B", install / "tools/run_motion_package.py", "--help"],
                cwd=root, capture_output=True, text=True, check=True,
            )
            self.assertIn("--sha256", result.stdout)
            self.assertIn("--toolchain", result.stdout)
