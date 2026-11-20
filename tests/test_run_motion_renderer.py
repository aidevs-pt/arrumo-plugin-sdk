import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.run_motion_renderer import run_renderer


class RenderWorkerTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.project = self.root / "composition"
        self.project.mkdir()
        self.output = self.root / "output"

    @patch("tools.run_motion_renderer.sys.platform", "linux")
    def test_sandbox_invocation_and_handoff(self):
        def render(argv, **options):
            self.assertIn("--unshare-all", argv)
            self.assertIn("--clearenv", argv)
            scratch = argv.index("--size")
            self.assertEqual(argv[scratch:scratch + 4], ["--size", "4096", "--tmpfs", "/tmp"])
            start = argv.index(str(self.project.resolve())) - 1
            self.assertEqual(argv[start:start + 3], ["--ro-bind", str(self.project.resolve()), "/input"])
            self.assertEqual(argv[-6:], [
                "--", "/usr/bin/prlimit", "--fsize=1024:1024", "--", "/input/render", "composition",
            ])
            self.assertEqual(options["timeout"], 15)
            (self.output / "preview.mp4").write_bytes(b"fixture")
            (self.output / "artifacts.json").write_text(json.dumps([{
                "kind": "animation", "title": "Product reveal", "usage_markdown": "",
                "preview": "/output/preview.mp4",
            }]), encoding="utf-8")

        with patch("tools.run_motion_renderer.subprocess.run", side_effect=render):
            batch = run_renderer(self.project, self.output, ["/input/render", "composition"], 15,
                                 max_output_bytes=1024, max_scratch_bytes=4096)
        self.assertEqual(batch[0]["preview"], str((self.output / "preview.mp4").resolve()))

    @patch("tools.run_motion_renderer.sys.platform", "linux")
    def test_refuses_overlapping_or_existing_output(self):
        with self.assertRaises(ValueError):
            run_renderer(self.project, self.project / "output", ["/input/render"], 15)
        self.output.mkdir()
        with self.assertRaises(FileExistsError):
            run_renderer(self.project, self.output, ["/input/render"], 15)

    @patch("tools.run_motion_renderer.sys.platform", "linux")
    def test_rejects_total_referenced_bytes_over_limit(self):
        def render(*args, **options):
            for filename in ("preview.mp4", "sound.wav"):
                (self.output / filename).write_bytes(b"1234")
            (self.output / "artifacts.json").write_text(json.dumps([{
                "kind": "transition", "title": "Wipe", "usage_markdown": "",
                "preview": "/output/preview.mp4", "sound": "/output/sound.wav",
            }]), encoding="utf-8")

        with patch("tools.run_motion_renderer.subprocess.run", side_effect=render):
            with self.assertRaisesRegex(ValueError, "exceed the output byte limit"):
                run_renderer(self.project, self.output, ["/input/render"], 15, max_output_bytes=6)
