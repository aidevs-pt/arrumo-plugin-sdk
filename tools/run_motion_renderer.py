#!/usr/bin/env python3
"""Run an operator-selected renderer in a local Linux Bubblewrap sandbox."""

import argparse
import json
import subprocess
import sys
from pathlib import Path

from jsonschema import ValidationError

if __package__:
    from .resolve_motion_artifacts import MAX_BATCH_BYTES, resolve_artifacts
else:
    from resolve_motion_artifacts import MAX_BATCH_BYTES, resolve_artifacts


DEFAULT_MAX_OUTPUT_BYTES = 512 * 1024 * 1024


def run_renderer(project, output, argv, timeout, toolchain=None, *, max_output_bytes=DEFAULT_MAX_OUTPUT_BYTES):
    if sys.platform != "linux":
        raise ValueError("The Bubblewrap runner requires Linux")
    if not argv or not argv[0].startswith(("/usr/bin/", "/renderer/", "/input/")):
        raise ValueError("Specify the renderer executable inside /usr/bin, /renderer, or /input")
    if timeout <= 0:
        raise ValueError("The timeout must be positive")
    if not isinstance(max_output_bytes, int) or not 0 < max_output_bytes <= 2**63 - 1:
        raise ValueError("The output byte limit must be a positive signed 64-bit integer")

    project = Path(project).resolve(strict=True)
    output = Path(output).resolve()
    if not project.is_dir():
        raise ValueError("The renderer project must be a directory")
    if output.is_relative_to(project) or project.is_relative_to(output):
        raise ValueError("Use disjoint project and output directories")
    if toolchain is not None:
        toolchain = Path(toolchain).resolve(strict=True)
        if not toolchain.is_dir() or output.is_relative_to(toolchain) or toolchain.is_relative_to(output):
            raise ValueError("Use a separate read-only toolchain directory")

    output.mkdir(mode=0o700)
    command = [
        "bwrap", "--unshare-all", "--die-with-parent", "--new-session",
        "--clearenv", "--setenv", "PATH", "/usr/bin", "--setenv", "HOME", "/tmp",
        "--ro-bind", "/usr", "/usr",
        "--symlink", "usr/lib", "/lib", "--symlink", "usr/lib64", "/lib64",
        "--dev", "/dev", "--proc", "/proc", "--tmpfs", "/tmp",
        "--ro-bind", str(project), "/input", "--bind", str(output), "/output",
        "--chdir", "/input",
    ]
    if toolchain is not None:
        command.extend(["--ro-bind", str(toolchain), "/renderer"])
    subprocess.run(
        [*command, "--", "/usr/bin/prlimit", f"--fsize={max_output_bytes}:{max_output_bytes}", "--", *argv],
        check=True, timeout=timeout,
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )

    manifest = output / "artifacts.json"
    if manifest.is_symlink() or not manifest.is_file():
        raise ValueError("The renderer must write a regular /output/artifacts.json file")
    with manifest.open("rb") as source:
        batch = source.read(MAX_BATCH_BYTES + 1)
    if len(batch) > MAX_BATCH_BYTES:
        raise ValueError("Motion artifact batch exceeds 128 KiB")
    artifacts = resolve_artifacts(json.loads(batch), output)
    files = {
        Path(item[role]) for item in artifacts
        for role in ("preview", "thumbnail", "sound") if item.get(role)
    }
    if sum(file.stat().st_size for file in files) > max_output_bytes:
        raise ValueError("Referenced motion artifacts exceed the output byte limit")
    return artifacts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--toolchain", type=Path)
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--max-output-bytes", type=int, default=DEFAULT_MAX_OUTPUT_BYTES)
    parser.add_argument("renderer", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    renderer = args.renderer[1:] if args.renderer[:1] == ["--"] else args.renderer
    try:
        print(json.dumps(run_renderer(
            args.project, args.output, renderer, args.timeout, args.toolchain,
            max_output_bytes=args.max_output_bytes,
        )))
    except subprocess.TimeoutExpired:
        parser.exit(1, "Renderer exceeded its time limit\n")
    except subprocess.CalledProcessError:
        parser.exit(1, "Renderer or Bubblewrap exited unsuccessfully\n")
    except (OSError, ValueError, ValidationError) as error:
        parser.exit(1, f"Cannot run motion renderer: {error}\n")


if __name__ == "__main__":
    main()
