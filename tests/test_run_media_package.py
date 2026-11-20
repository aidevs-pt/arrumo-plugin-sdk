import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from tools.run_media_package import run_media_package


class MediaPackageTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.package = self.root / "media.zip"
        self.inputs = self.root / "media"
        self.inputs.mkdir()
        self.output = self.root / "output"
        with zipfile.ZipFile(self.package, "w") as archive:
            archive.writestr("tools/worker.py", "print('test')")
        self.digest = hashlib.sha256(self.package.read_bytes()).hexdigest()

    def run_worker(self, digest):
        return run_media_package(self.package, digest, self.inputs, self.output, ["tools/worker.py"], 12)

    @patch("tools.run_media_package.run_sandbox")
    def test_passes_reviewed_python_entrypoint_and_explicit_media_directory(self, sandbox):
        def execute(project, output, argv, timeout, *, inputs):
            self.assertTrue((project / "tools/worker.py").is_file())
            self.assertEqual(argv[-1], "/input/tools/worker.py")
            self.assertEqual((inputs, timeout), (self.inputs, 12))
            output.mkdir()
            (output / "a.wav").write_bytes(b"fixture")
            (output / "result.json").write_text(json.dumps({"file": "a.wav"}), encoding="utf-8")
            return output

        sandbox.side_effect = execute
        with self.assertRaisesRegex(ValueError, "digest"):
            self.run_worker("0" * 64)
        sandbox.assert_not_called()
        self.assertEqual(self.run_worker(self.digest), self.output / "a.wav")

    @patch("tools.run_media_package.run_sandbox")
    def test_rejects_artifact_outside_output(self, sandbox):
        self.output.mkdir()
        (self.output / "result.json").write_text('{"file":"../a.wav"}', encoding="utf-8")
        sandbox.return_value = self.output
        with self.assertRaisesRegex(ValueError, "named MP4 or WAV"):
            self.run_worker(self.digest)
