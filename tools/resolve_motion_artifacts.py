#!/usr/bin/env python3
"""Translate an isolated renderer's finished artifact batch for the Arrumo host."""

import argparse
import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator, ValidationError


SCHEMA_PATH = Path(__file__).resolve().parents[1] / "motion-artifacts.schema.json"
SCHEMA = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
VALIDATOR = Draft202012Validator(SCHEMA)
MAX_BATCH_BYTES = 128 * 1024


def resolve_artifacts(batch, output_directory):
    VALIDATOR.validate(batch)
    root = Path(output_directory).resolve(strict=True)
    if not root.is_dir():
        raise ValueError("The host output directory must be a directory")

    resolved = []
    for artifact in batch:
        item = artifact.copy()
        for role in ("preview", "thumbnail", "sound"):
            virtual_path = item.get(role)
            if virtual_path is None:
                continue
            components = virtual_path.split("/")
            if components[:2] != ["", "output"] or len(components) < 3:
                raise ValueError(f"{role} must name a file under /output")
            relative = components[2:]
            if any(part in ("", ".", "..") or "\\" in part or ":" in part for part in relative):
                raise ValueError(f"{role} contains an invalid output path component")
            candidate = root.joinpath(*relative)
            real_path = candidate.resolve(strict=True)
            if not real_path.is_relative_to(root) or not real_path.is_file():
                raise ValueError(f"{role} must resolve to a regular file under the host output directory")
            item[role] = str(real_path)
        resolved.append(item)
    return resolved


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_directory", type=Path)
    args = parser.parse_args()
    try:
        payload = sys.stdin.buffer.read(MAX_BATCH_BYTES + 1)
        if len(payload) > MAX_BATCH_BYTES:
            raise ValueError("Motion artifact batch exceeds 128 KiB")
        batch = json.loads(payload)
        print(json.dumps(resolve_artifacts(batch, args.output_directory)))
    except (OSError, ValueError, ValidationError) as error:
        parser.exit(1, f"Cannot resolve motion artifacts: {error}\n")


if __name__ == "__main__":
    main()
