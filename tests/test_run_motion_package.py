import hashlib
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from tools.package_plugin import build_package
from tools.run_motion_package import run_package


class MotionPackageTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        (self.root / "manifest.json").write_text(json.dumps({
            "schemaVersion": 1, "id": "fixture-render", "name": "Fixture",
            "description": "Fixture", "capabilities": {
                "motion-render": {"name": "Motion render", "description": "Render motion."},
            },
        }), encoding="utf-8")
        (self.root / "renderer.json").write_text('{"entrypoint":"render.sh"}', encoding="utf-8")
        (self.root / "render.sh").write_text("exit 0\n", encoding="utf-8")
        data, info = build_package(self.root, ["render.sh", "renderer.json"])
        self.path = self.root / "renderer.zip"
        self.path.write_bytes(data)
        self.digest = info["sha256"]
        self.output = self.root / "output"

    def test_dispatch_uses_verified_package_script(self):
        def launch(project, output, argv, timeout, toolchain):
            self.assertEqual((project / "render.sh").read_text(), "exit 0\n")
            self.assertEqual(output, self.output)
            self.assertEqual(argv, ["/usr/bin/sh", "/input/render.sh"])
            return ["fixture"]

        with patch("tools.run_motion_package.run_renderer", side_effect=launch):
            self.assertEqual(run_package(self.path, self.digest, self.output, 15), ["fixture"])

    def test_rejects_unreviewed_and_traversing_packages(self):
        with self.assertRaisesRegex(ValueError, "digest"):
            run_package(self.path, "0" * 64, self.output, 15)
        with zipfile.ZipFile(self.path, "a") as archive:
            archive.writestr("../escape.sh", "exit 0")
        digest = hashlib.sha256(self.path.read_bytes()).hexdigest()
        with self.assertRaisesRegex(ValueError, "Unsafe package path"):
            run_package(self.path, digest, self.output, 15)
        self.assertFalse((self.root / "escape.sh").exists())
        self.assertFalse(self.output.exists())
