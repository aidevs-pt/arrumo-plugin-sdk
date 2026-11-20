#!/usr/bin/env python3
"""Run an explicitly reviewed motion-render plugin ZIP in the Linux worker."""

import argparse
import hashlib
import hmac
import io
import json
import stat
import sys
import tempfile
import zipfile
from pathlib import Path
from subprocess import SubprocessError

from jsonschema import Draft202012Validator, ValidationError

if __package__:
    from .package_plugin import MAX_MANIFEST, MAX_PACKAGE, SCHEMA, unique_fields, validate_package_paths
    from .run_motion_renderer import run_renderer
else:
    from package_plugin import MAX_MANIFEST, MAX_PACKAGE, SCHEMA, unique_fields, validate_package_paths
    from run_motion_renderer import run_renderer


def run_package(package, digest, output, timeout, toolchain=None):
    with Path(package).open("rb") as source:
        data = source.read(MAX_PACKAGE + 1)
    if len(data) > MAX_PACKAGE:
        raise ValueError("Motion package exceeds 16 MiB")
    if not hmac.compare_digest(hashlib.sha256(data).hexdigest(), digest):
        raise ValueError("Motion package digest does not match the reviewed ZIP")

    with zipfile.ZipFile(io.BytesIO(data)) as archive, tempfile.TemporaryDirectory() as temporary:
        entries = archive.infolist()
        names = [entry.filename for entry in entries]
        validate_package_paths(names)
        if sum(entry.file_size for entry in entries) > MAX_PACKAGE:
            raise ValueError("Expanded motion package exceeds 16 MiB")
        for entry in entries:
            mode = entry.external_attr >> 16
            if entry.is_dir() or stat.S_IFMT(mode) not in (0, stat.S_IFREG):
                raise ValueError("Motion package entries must be regular files")

        def read_json(name):
            try:
                entry = archive.getinfo(name)
            except KeyError as error:
                raise ValueError(f"Motion package is missing {name}") from error
            if entry.file_size > MAX_MANIFEST:
                raise ValueError(f"{name} exceeds the metadata limit")
            return json.loads(archive.read(entry).decode("utf-8"), object_pairs_hook=unique_fields)

        manifest = read_json("manifest.json")
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        Draft202012Validator(schema).validate(manifest)
        if "motion-render" not in manifest["capabilities"]:
            raise ValueError("Motion package must declare the motion-render capability")
        descriptor = read_json("renderer.json")
        if (not isinstance(descriptor, dict) or set(descriptor) != {"entrypoint"}
                or not isinstance(descriptor["entrypoint"], str)):
            raise ValueError("renderer.json must declare a single script entrypoint")
        entrypoint = descriptor["entrypoint"]
        if not entrypoint.endswith(".sh") or entrypoint not in names or archive.getinfo(entrypoint).file_size == 0:
            raise ValueError("The renderer entrypoint must name a non-empty packaged shell script")

        project = Path(temporary)
        for entry in entries:
            destination = project.joinpath(*entry.filename.split("/"))
            destination.parent.mkdir(parents=True, exist_ok=True)
            with destination.open("xb") as target:
                target.write(archive.read(entry))
        return run_renderer(project, output, ["/usr/bin/sh", f"/input/{entrypoint}"], timeout, toolchain)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package", type=Path)
    parser.add_argument("--sha256", required=True, help="SHA-256 from a reviewed package record")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--toolchain", type=Path)
    args = parser.parse_args()
    if len(args.sha256) != 64 or any(c not in "0123456789abcdef" for c in args.sha256):
        parser.error("--sha256 must be 64 lowercase hex digits")
    try:
        result = run_package(args.package, args.sha256, args.output, args.timeout, args.toolchain)
        print(json.dumps(result))
    except (OSError, ValueError, ValidationError, zipfile.BadZipFile, SubprocessError) as error:
        parser.exit(1, f"Cannot run renderer package: {error}\n")


if __name__ == "__main__":
    main()
