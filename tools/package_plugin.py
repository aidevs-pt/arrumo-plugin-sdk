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
MAX_ICON = 8 * 1024
SCHEMA_DIR = Path(__file__).resolve().parent.parent
SCHEMA = SCHEMA_DIR / "manifest.schema.json"
ADAPTERS = {
    "transcription.json": ("transcription.schema.json", "transcription"),
    "transcription-timed.json": ("transcription.schema.json", "transcription"),
    "speech-synthesis.json": ("speech-synthesis.schema.json", "text-to-speech"),
    "image-generation.json": ("image-generation.schema.json", "image-generation"),
    "video-generation.json": ("video-generation.schema.json", "video-generation"),
}


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


def validate_package_paths(names):
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

def template_uses(value, placeholder):
    if isinstance(value, dict):
        return any(template_uses(item, placeholder) for item in value.values())
    if isinstance(value, list):
        return any(template_uses(item, placeholder) for item in value)
    return value == placeholder


def validate_adapter(name, data, manifest):
    schema_name, capability = ADAPTERS[name]
    schema = json.loads((SCHEMA_DIR / schema_name).read_text(encoding="utf-8"))
    descriptor = json.loads(data.decode("utf-8"), object_pairs_hook=unique_fields)
    Draft202012Validator(schema).validate(descriptor)
    if descriptor["pluginId"] != manifest["id"] or capability not in manifest["capabilities"]:
        raise ValueError(f"Adapter does not match the manifest identity and capabilities: {name}")
    credential = next(
        (setting for setting in manifest.get("settings", [])
         if setting["id"] == descriptor["credentialSetting"] and setting["kind"] == "secret"),
        None,
    )
    if credential is None or (capability in ("text-to-speech", "video-generation") and credential["scope"] != "workspace"):
        raise ValueError(f"Adapter requires a matching secret setting: {name}")
    if name == "image-generation.json":
        model_setting = descriptor["model"].get("setting")
        if model_setting is not None and not any(
            setting["id"] == model_setting and setting["kind"] == "string"
            for setting in manifest.get("settings", [])
        ):
            raise ValueError("Image adapter model setting must be a declared string setting")
        if not template_uses(descriptor["request"], "{prompt}"):
            raise ValueError("Image adapter request must contain {prompt}")
    if name == "video-generation.json":
        durations = descriptor["durations"]
        if not durations["min"] <= durations["default"] <= durations["max"]:
            raise ValueError("Video adapter durations must satisfy min <= default <= max")
        if not template_uses(descriptor["request"], "{prompt}"):
            raise ValueError("Video adapter request must contain {prompt}")
    if name == "transcription-timed.json" and "words" not in descriptor["response"]:
        raise ValueError("Timed transcription adapter requires a timing mapping")


def build_package(root, extra_files):
    manifest_bytes = read_file(root, "manifest.json", MAX_MANIFEST)
    manifest = json.loads(manifest_bytes.decode("utf-8"), object_pairs_hook=unique_fields)
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(manifest)
    # The declared icon always travels with the package.
    icon = manifest.get("icon")
    names = ["manifest.json", *extra_files, *([icon] if icon and icon not in extra_files else [])]
    validate_package_paths(names)
    setting_ids = [setting["id"] for setting in manifest.get("settings", [])]
    if len(setting_ids) != len(set(setting_ids)):
        raise ValueError("Duplicate plugin setting ID")

    action_ids = [action["id"] for action in manifest.get("actions", [])]
    if len(action_ids) != len(set(action_ids)):
        raise ValueError("Duplicate plugin action ID")
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
                limit = min(remaining, MAX_MANIFEST) if name in ADAPTERS else remaining
                if name == icon:
                    limit = min(limit, MAX_ICON)
                data = read_file(root, name, limit)
                remaining -= len(data)
                if name in ADAPTERS:
                    validate_adapter(name, data, manifest)
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
