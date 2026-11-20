import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads((ROOT / "motion-artifacts.schema.json").read_text(encoding="utf-8"))
EXAMPLE = json.loads((ROOT / "examples/motion-artifacts.json").read_text(encoding="utf-8"))


class MotionArtifactsTests(unittest.TestCase):
    def test_accepts_local_absolute_paths(self):
        Draft202012Validator.check_schema(SCHEMA)
        validator = Draft202012Validator(SCHEMA)
        self.assertTrue(validator.is_valid(EXAMPLE))
        for path in (r"C:\output\preview.mp4", r"\\server\renders\preview.mp4"):
            with self.subTest(path=path):
                self.assertTrue(validator.is_valid([{**EXAMPLE[0], "preview": path, "sound": None}]))

    def test_rejects_invalid_batches(self):
        validator = Draft202012Validator(SCHEMA)
        self.assertFalse(validator.is_valid([]))
        for fields in (
            {"preview": "preview.mp4"},
            {"preview": "https://example.org/preview.mp4"},
            {"preview": r"C:preview.mp4"},
            {"preview": "/output/preview\0.mp4"},
            {"sound": 12},
            {"profile_id": 0},
            {"preview_asset_id": 12},
        ):
            with self.subTest(fields=fields):
                self.assertFalse(validator.is_valid([EXAMPLE[0], {**EXAMPLE[0], **fields}]))
