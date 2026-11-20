#!/usr/bin/env python3
"""Build a deterministic Linux SDK worker bundle for an extracted installation."""

import argparse
from hashlib import sha256
from pathlib import Path
from zipfile import ZipFile, ZipInfo


ROOT = Path(__file__).resolve().parents[1]
FILES = (
    "LICENSE",
    "manifest.schema.json",
    "motion-artifacts.schema.json",
    "motion-worker-requirements.txt",
    "tools/package_plugin.py",
    "tools/resolve_motion_artifacts.py",
    "tools/run_motion_package.py",
    "tools/run_motion_renderer.py",
)


def build(output):
    with ZipFile(output, "x") as archive:
        for name in FILES:
            entry = ZipInfo(name)
            entry.create_system = 3
            entry.external_attr = 0o100644 << 16
            archive.writestr(entry, (ROOT / name).read_bytes())
    return sha256(output.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    try:
        print(build(args.output))
    except OSError as error:
        parser.exit(1, f"Cannot package motion worker: {error}\n")


if __name__ == "__main__":
    main()
