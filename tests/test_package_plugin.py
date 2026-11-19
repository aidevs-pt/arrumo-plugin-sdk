import hashlib
import io
import os
from pathlib import Path
import tempfile
import unittest
import zipfile

from tools.package_plugin import build_package


class PackagePluginTest(unittest.TestCase):
    def setUp(self):
        directory = self.enterContext(tempfile.TemporaryDirectory())
        self.source = Path(directory)
        self.manifest = Path("examples/transcription.json").read_bytes()
        (self.source / "manifest.json").write_bytes(self.manifest)
        (self.source / "LICENSE").write_text("fixture", encoding="utf-8")
        (self.source / "README.md").write_text("fixture", encoding="utf-8")

    def test_build_is_reproducible_and_contains_only_selected_files(self):
        (self.source / ".env").write_text("fixture", encoding="utf-8")
        first, metadata = build_package(self.source, ["README.md", "LICENSE"])
        os.utime(self.source / "README.md", (0, 0))
        second, _ = build_package(self.source, ["LICENSE", "README.md"])
        self.assertEqual(first, second)
        self.assertEqual(metadata["sha256"], hashlib.sha256(first).hexdigest())
        with zipfile.ZipFile(io.BytesIO(first)) as archive:
            self.assertEqual(archive.namelist(), ["LICENSE", "README.md", "manifest.json"])
            self.assertEqual(archive.read("manifest.json"), self.manifest)

    def test_rejects_duplicate_paths_and_traversal(self):
        for path in ("MANIFEST.JSON", "../README.md", "a\\b", "/README.md"):
            with self.subTest(path=path), self.assertRaises(ValueError):
                build_package(self.source, [path])

    def test_rejects_symlinked_files_and_parent_directories(self):
        (self.source / "linked.txt").symlink_to("README.md")
        (self.source / "real").mkdir()
        (self.source / "real" / "payload.txt").write_text("fixture", encoding="utf-8")
        (self.source / "linked").symlink_to("real", target_is_directory=True)
        for path in ("linked.txt", "linked/payload.txt"):
            with self.subTest(path=path), self.assertRaisesRegex(ValueError, "Symbolic links"):
                build_package(self.source, [path])

    def test_rejects_duplicate_and_unsupported_manifest_data(self):
        from jsonschema import ValidationError

        manifest = self.source / "manifest.json"
        manifest.write_bytes(b'{"id":"first","id":"second"}')
        with self.assertRaisesRegex(ValueError, "Duplicate manifest field"):
            build_package(self.source, [])
        manifest.write_bytes(self.manifest.replace(b'"schemaVersion": 2', b'"schemaVersion": 5'))
        with self.assertRaises(ValidationError):
            build_package(self.source, [])

    def test_requires_nonempty_backend_and_frontend_entrypoints(self):
        import json

        manifest = json.loads(self.manifest)
        manifest["schemaVersion"] = 3
        manifest["code"] = {
            "backend": {"component": "component.wasm"},
            "frontend": [{
                "id": "fixture-panel",
                "document": "index.html",
                "title": "Fixture",
                "placement": "workspace",
            }],
        }
        (self.source / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        (self.source / "component.wasm").write_bytes(b"\0asm\r\0\1\0")
        (self.source / "index.html").write_text("<p>Fixture</p>", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Include every declared"):
            build_package(self.source, ["component.wasm"])
        package, metadata = build_package(self.source, ["component.wasm", "index.html"])
        self.assertEqual(metadata["manifestSchemaVersion"], 3)
        with zipfile.ZipFile(io.BytesIO(package)) as archive:
            self.assertIn("component.wasm", archive.namelist())
            self.assertIn("index.html", archive.namelist())
