import hashlib
from pathlib import Path
import stat
import tempfile
import unittest
import zipfile

from tools.stage_plugin_package import stage_files


class StagePluginPackageTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.package = self.root / "fixture.zip"
        self.output = self.root / "staged"

    def write_entries(self, entries):
        with zipfile.ZipFile(self.package, "w") as archive:
            for entry in entries:
                archive.writestr(entry, b"fixture")
        return hashlib.sha256(self.package.read_bytes()).hexdigest()

    def test_stages_only_requested_files_from_reviewed_archive(self):
        digest = self.write_entries(["tools/worker.py", "README.md"])
        stage_files(self.package, digest, self.output, ["tools/worker.py"])
        self.assertEqual((self.output / "tools/worker.py").read_bytes(), b"fixture")
        self.assertFalse((self.output / "README.md").exists())
        with self.assertRaises(FileExistsError):
            stage_files(self.package, digest, self.output, ["README.md"])

    def test_failed_staging_does_not_publish_partial_files(self):
        digest = self.write_entries(["tools/worker.py"])
        for checksum, names in [
            ("0" * 64, ["tools/worker.py"]),
            (digest, ["tools/worker.py", "missing.py"]),
            (digest, ["../outside.py"]),
        ]:
            with self.assertRaises(ValueError):
                stage_files(self.package, checksum, self.output, names)
            self.assertFalse(self.output.exists())

    def test_rejects_unsafe_members_even_when_not_requested(self):
        link = zipfile.ZipInfo("link.py")
        link.create_system = 3
        link.external_attr = stat.S_IFLNK << 16
        for entry in [link, "TOOLS/WORKER.PY", "../escape"]:
            digest = self.write_entries(["tools/worker.py", entry])
            with self.assertRaises(ValueError):
                stage_files(self.package, digest, self.output, ["tools/worker.py"])
            self.assertFalse(self.output.exists())
