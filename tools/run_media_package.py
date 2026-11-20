#!/usr/bin/env python3
"""Run a reviewed plugin media worker in the network-isolated Linux sandbox."""
import argparse
import json
from pathlib import Path
import tempfile
import zipfile
from subprocess import SubprocessError

if __package__:
    from .package_plugin import unique_fields
    from .run_motion_renderer import run_sandbox, DEFAULT_MAX_OUTPUT_BYTES
    from .stage_plugin_package import stage_files
else:
    from package_plugin import unique_fields
    from run_motion_renderer import run_sandbox, DEFAULT_MAX_OUTPUT_BYTES
    from stage_plugin_package import stage_files


def run_media_package(package, digest, inputs, output, files, timeout):
    if not files or not files[0].endswith(".py"):
        raise ValueError("The first selected file must be the Python worker entrypoint")
    with tempfile.TemporaryDirectory(prefix="arrumo-media-worker-") as temporary:
        project = Path(temporary) / "project"
        stage_files(package, digest, project, files)
        output = run_sandbox(
            project, output, ["/usr/bin/python3", "-E", "-s", "-B", f"/input/{files[0]}"],
            timeout, inputs=inputs,
        )
    result = output / "result.json"
    if result.is_symlink() or not result.is_file():
        raise ValueError("Worker must publish a regular result.json")
    with result.open("rb") as stream:
        metadata = stream.read(8193)
    if len(metadata) > 8192:
        raise ValueError("Worker result metadata exceeds 8 KiB")
    document = json.loads(metadata, object_pairs_hook=unique_fields)
    if not isinstance(document, dict) or set(document) != {"file"}:
        raise ValueError("Worker result must identify one artifact")
    name = document["file"]
    if not isinstance(name, str) or Path(name).name != name or Path(name).suffix not in {".mp4", ".wav"}:
        raise ValueError("Worker artifact must be a named MP4 or WAV")
    artifact = output / name
    if artifact.is_symlink() or not artifact.is_file() or not 0 < artifact.stat().st_size <= DEFAULT_MAX_OUTPUT_BYTES:
        raise ValueError("Worker artifact is unavailable or exceeds the size limit")
    return artifact


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package", type=Path)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--entrypoint", required=True)
    parser.add_argument("--include", action="append", default=[])
    parser.add_argument("--timeout", type=int, default=120)
    args = parser.parse_args()
    try:
        artifact = run_media_package(
            args.package, args.sha256, args.inputs, args.output,
            [args.entrypoint, *args.include], args.timeout,
        )
        print(json.dumps({"file": str(artifact)}))
    except (OSError, ValueError, RuntimeError, NotImplementedError, SubprocessError, zipfile.BadZipFile) as error:
        parser.exit(1, f"{error}\n")


if __name__ == "__main__":
    main()
