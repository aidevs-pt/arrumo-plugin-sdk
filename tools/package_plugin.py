#!/usr/bin/env python3
"""Build an Arrumo plugin ZIP from explicitly selected files."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import stat
import zipfile

from jsonschema import Draft202012Validator, ValidationError

MAX_PACKAGE = 16 * 1024 * 1024
MAX_MANIFEST = 64 * 1024
MAX_ENTRIES = 512
SCHEMA = Path(__file__).resolve().parent.parent / "manifest.schema.json"


def read_file(root, name, limit):
    path = root
    for part in name.split("/"):
        path /= part
        if path.is_symlink():
            raise ValueError(f"Symbolic links are forbidden: {name}")
    if not path.is_file():
        raise ValueError(f"Expected a regular file: {name}")
    with path.open("rb") as file:
        data = file.read(limit + 1)
    if len(data) > limit:
        raise ValueError(f"File exceeds the available package size limit: {name}")
    return data


def unique_fields(pairs):
    fields = {}
    for key, value in pairs:
        if key in fields:
            raise ValueError(f"Duplicate manifest field: {key}")
        fields[key] = value
    return fields


def build_package(root, extra_files):
    names = ["manifest.json", *extra_files]
    if len(names) > MAX_ENTRIES:
        raise ValueError("A package can contain at most 512 files")
    folded = set()
    for name in names:
        if any(
            part in {"", ".", "..", ".git"}
            or any(c in "\\:" or ord(c) < 32 or 127 <= ord(c) <= 159 for c in part)
            for part in name.split("/")
        ):
            raise ValueError(f"Unsafe package path: {name}")
        canonical = name.lower()
        if canonical in folded:
            raise ValueError(f"Duplicate package path: {name}")
        folded.add(canonical)

    manifest_bytes = read_file(root, "manifest.json", MAX_MANIFEST)
    manifest = json.loads(manifest_bytes.decode("utf-8"), object_pairs_hook=unique_fields)
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(manifest)
    setting_ids = [setting["id"] for setting in manifest.get("settings", [])]
    if len(setting_ids) != len(set(setting_ids)):
        raise ValueError("Duplicate plugin setting ID")

    code = manifest.get("code", {})
    surfaces = code.get("frontend", [])
    if len({surface["id"] for surface in surfaces}) != len(surfaces):
        raise ValueError("Duplicate plugin surface ID")
    entrypoints = {surface["document"] for surface in surfaces}
    if "backend" in code:
        entrypoints.add(code["backend"]["component"])
    if not entrypoints.issubset(names):
        raise ValueError("Include every declared code entrypoint in the package")

    buffer = io.BytesIO()
    remaining = MAX_PACKAGE - len(manifest_bytes)
    with zipfile.ZipFile(buffer, "w") as archive:
        for name in sorted(names):
            if name == "manifest.json":
                data = manifest_bytes
            else:
                data = read_file(root, name, remaining)
                remaining -= len(data)
            if name in entrypoints and not data:
                raise ValueError(f"Empty plugin code entrypoint: {name}")
            entry = zipfile.ZipInfo(name)
            entry.create_system = 3
            entry.external_attr = (stat.S_IFREG | 0o644) << 16
            archive.writestr(entry, data)
    package = buffer.getvalue()
    if len(package) > MAX_PACKAGE:
        raise ValueError("ZIP including headers exceeds 16 MiB")

    return package, {
        "id": manifest["id"],
        "manifestSchemaVersion": manifest["schemaVersion"],
        "sha256": hashlib.sha256(package).hexdigest(),
        "byteLength": len(package),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="directory containing manifest.json")
    parser.add_argument("output", type=Path, help="new ZIP file to create")
    parser.add_argument("--include", metavar="PATH", action="append", default=[])
    args = parser.parse_args()
    try:
        package, metadata = build_package(args.source, args.include)
        with args.output.open("xb") as output:
            output.write(package)
    except (OSError, ValueError, ValidationError) as error:
        parser.exit(1, f"{error}\n")
    print(json.dumps(metadata, sort_keys=True))


if __name__ == "__main__":
    main()
