import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads((ROOT / "motion-result.schema.json").read_text(encoding="utf-8"))
EXAMPLE = json.loads((ROOT / "examples/motion-result.json").read_text(encoding="utf-8"))


class MotionResultTests(unittest.TestCase):
    def test_example_and_metadata(self):
        Draft202012Validator.check_schema(SCHEMA)
        validator = Draft202012Validator(SCHEMA)
        self.assertTrue(validator.is_valid(EXAMPLE))
        self.assertTrue(validator.is_valid({**EXAMPLE, "summary": "Overlay ready"}))
        self.assertTrue(validator.is_valid({"motion_items": []}))

    def test_rejects_invalid_items(self):
        validator = Draft202012Validator(SCHEMA)
        item = EXAMPLE["motion_items"][0]
        for invalid_fields in (
            {"preview_asset_id": "video.mp4"},
            {"preview_asset_id": 0},
            {"profile_id": -1},
            {"title": "  "},
            {"kind": "still"},
            {"preview_path": "/tmp/preview.mp4"},
        ):
            with self.subTest(invalid_fields=invalid_fields):
                self.assertFalse(validator.is_valid({"motion_items": [{**item, **invalid_fields}]}))
