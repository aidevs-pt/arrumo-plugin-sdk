import tempfile
import unittest
from pathlib import Path

from tools.resolve_motion_artifacts import resolve_artifacts


class ResolveMotionArtifactsTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.workspace = Path(directory.name)
        self.output = self.workspace / "job-output"
        self.output.mkdir()

    def artifact(self, preview):
        return {
            "kind": "transition", "title": "Wipe",
            "usage_markdown": "", "preview": preview, "sound": None,
        }

    def test_translates_only_media_fields(self):
        media = self.output / "space in name.mp4"
        media.touch()
        item = self.artifact("/output/space in name.mp4")
        batch = resolve_artifacts([item], self.output)
        self.assertEqual(batch, [{**item, "preview": str(media.resolve())}])
        self.assertEqual(item["preview"], "/output/space in name.mp4")

    def test_rejects_paths_outside_mount_and_non_files(self):
        for value in ("/tmp/preview.mp4", "/output/../preview.mp4", "/output/C:/preview.mp4"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                resolve_artifacts([self.artifact(value)], self.output)
        (self.output / "directory").mkdir()
        with self.assertRaises(ValueError):
            resolve_artifacts([self.artifact("/output/directory")], self.output)
        with self.assertRaises(FileNotFoundError):
            resolve_artifacts([self.artifact("/output/missing.mp4")], self.output)

    def test_rejects_a_symlink_outside_the_mount(self):
        outside = self.workspace / "outside.mp4"
        outside.touch()
        try:
            (self.output / "alias.mp4").symlink_to(outside)
        except OSError as error:
            self.skipTest(f"Symlink unavailable: {error}")
        with self.assertRaises(ValueError):
            resolve_artifacts([self.artifact("/output/alias.mp4")], self.output)
