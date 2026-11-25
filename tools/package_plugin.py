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
# Provider adapters list every model a provider offers, so they outgrow a manifest.
MAX_ADAPTER = 256 * 1024
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
    "audio-transform.json": ("audio-transform.schema.json", None),
    "dubbing.json": ("dubbing.schema.json", "dubbing"),
    # Each kind it declares needs its own capability, checked below.
    "audio-generation.json": ("audio-generation.schema.json", None),
    # Usage belongs to the provider rather than one capability.
    "usage.json": ("usage.schema.json", None),
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
    if descriptor["pluginId"] != manifest["id"] or (capability is not None and capability not in manifest["capabilities"]):
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
        models = descriptor.get("models")
        if models is not None:
            if descriptor["schemaVersion"] < 3:
                raise ValueError("Image adapter models need schema 3")
            check_model_choice(manifest, descriptor["model"], models, "Image")
            for model_id, model in models.items():
                if not template_uses(model["request"], "{prompt}"):
                    raise ValueError(f"Image model {model_id} request must contain {{prompt}}")
                if not {"16:9", "9:16", "1:1"} <= set(model["aspectRatios"]):
                    raise ValueError(f"Image model {model_id} must map 16:9, 9:16 and 1:1")
                check_single_reference(model.get("references"), f"Image model {model_id}")
        check_single_reference(descriptor.get("references"), "Image adapter")
    if name == "dubbing.json":
        if "{id}" not in descriptor["status"]["endpoint"].split("/") or "{language}" in descriptor["status"]["endpoint"]:
            raise ValueError("The dubbing status endpoint needs {id} and no {language}")
        if not {"{id}", "{language}"} <= set(descriptor["result"]["endpoint"].split("/")):
            raise ValueError("The dubbing result endpoint needs {id} and {language}")
        if credential["scope"] != "workspace":
            raise ValueError("Dubbing adapter requires a workspace secret")
    if name == "audio-transform.json":
        for transform, capability in (("voice-change", "voice-changer"), ("voice-isolation", "voice-isolation")):
            if transform in descriptor["transforms"] and capability not in manifest["capabilities"]:
                raise ValueError(f"Audio transform {transform} needs the {capability} capability")
        entry = descriptor["transforms"].get("voice-change")
        if entry and (not entry["voiceSegment"] or "voiceSetting" not in descriptor):
            raise ValueError("The voice-change transform needs a voice segment and a voice setting")
        if credential["scope"] != "workspace":
            raise ValueError("Audio transform adapter requires a workspace secret")
    if name == "speech-synthesis.json" and "models" in descriptor:
        if descriptor["schemaVersion"] < 2 or "model" not in descriptor:
            raise ValueError("Speech adapter models need schema 2 and a model choice")
        check_model_choice(manifest, descriptor["model"], descriptor["models"], "Speech")
        for model_id, model in descriptor["models"].items():
            if descriptor["textField"] in model["body"]:
                raise ValueError(f"Speech model {model_id} sets the text field in its body")
    if name == "video-generation.json":
        check_durations(descriptor["durations"], descriptor["schemaVersion"], "Video adapter")
        if not template_uses(descriptor["request"], "{prompt}"):
            raise ValueError("Video adapter request must contain {prompt}")
        models = descriptor.get("models")
        if models is not None:
            check_model_choice(manifest, descriptor.get("model", {}), models, "Video")
            for model_id, model in models.items():
                if isinstance(model, dict) and descriptor["schemaVersion"] < 3:
                    raise ValueError(f"Video model {model_id} needs schema 3 for label and bestFor")
                for variant in model["variants"] if isinstance(model, dict) else model:
                    check_video_variant(variant, descriptor["schemaVersion"], f"Video model {model_id}")
    if name == "audio-generation.json":
        for kind, entry in descriptor["kinds"].items():
            if f"{kind}-generation" not in manifest["capabilities"]:
                raise ValueError(f"Audio adapter kind {kind} needs the {kind}-generation capability")
            if entry["minSeconds"] > entry["maxSeconds"]:
                raise ValueError(f"Audio adapter kind {kind} must satisfy minSeconds <= maxSeconds")
            if entry["promptField"] == entry["durationField"] or {entry["promptField"], entry["durationField"]} & set(entry["body"]):
                raise ValueError(f"Audio adapter kind {kind} sets its prompt or duration twice")
        if credential["scope"] != "workspace":
            raise ValueError("Audio adapter requires a workspace secret")
    if name == "transcription-timed.json" and "words" not in descriptor["response"]:
        raise ValueError("Timed transcription adapter requires a timing mapping")


def check_model_choice(manifest, choice, models, kind):
    if choice.get("default") not in models:
        raise ValueError(f"{kind} adapter default model must be one of its models")
    setting_id = choice.get("setting")
    setting = next((item for item in manifest.get("settings", []) if item["id"] == setting_id), None)
    if setting_id is not None and (setting is None or set(setting.get("choices", [])) != set(models)):
        raise ValueError(f"{kind} adapter model setting choices must match its models")


def check_single_reference(references, owner):
    if references and references.get("single") and references["maxImages"] != 1:
        raise ValueError(f"{owner} sends a single reference, so maxImages must be 1")


def check_durations(durations, schema_version, owner):
    if not durations["min"] <= durations["default"] <= durations["max"]:
        raise ValueError(f"{owner} durations must satisfy min <= default <= max")
    allowed = durations.get("allowed")
    if allowed is not None:
        if schema_version < 3:
            raise ValueError(f"{owner} durations allowed needs schema 3")
        if durations["default"] not in allowed or not all(durations["min"] <= value <= durations["max"] for value in allowed):
            raise ValueError(f"{owner} durations allowed must lie within min and max and include default")


def check_video_variant(variant, schema_version, owner):
    if not template_uses(variant["request"], "{prompt}"):
        raise ValueError(f"{owner} request must contain {{prompt}}")
    if "durations" in variant:
        check_durations(variant["durations"], schema_version, owner)
    elif schema_version < 3 or variant.get("videos", {}).get("min", 0) < 1 or template_uses(variant["request"], "{duration}"):
        raise ValueError(f"{owner} variants without durations need schema 3, a reference video and no {{duration}}")
    if template_uses(variant["request"], "{lastImage}") and (schema_version < 3 or variant.get("images", {}).get("max") != 2):
        raise ValueError(f"{owner} uses {{lastImage}}, which needs schema 3 and at most two images")


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
                limit = min(remaining, MAX_ADAPTER) if name in ADAPTERS else remaining
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
