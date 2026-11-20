#!/usr/bin/env python3
"""Stage explicitly selected files from a digest-reviewed Arrumo plugin ZIP."""
import argparse
import hashlib
import hmac
import io
from pathlib import Path
import re
import stat
import tempfile
import zipfile

if __package__:
    from .package_plugin import MAX_PACKAGE, validate_package_paths
else:
    from package_plugin import MAX_PACKAGE, validate_package_paths


def stage_files(package, digest, output, names):
    if not re.fullmatch(r"[a-fA-F0-9]{64}", digest):
        raise ValueError("Expected a reviewed SHA-256 digest")
    if output.exists() or output.is_symlink():
        raise FileExistsError("Staging directory already exists")
    validate_package_paths(names)
    with package.open("rb") as source:
        data = source.read(MAX_PACKAGE + 1)
    if len(data) > MAX_PACKAGE:
        raise ValueError("Plugin package exceeds 16 MiB")
    if not hmac.compare_digest(hashlib.sha256(data).hexdigest(), digest.lower()):
        raise ValueError("Plugin package digest does not match the reviewed ZIP")

    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        entries = archive.infolist()
        validate_package_paths([entry.filename for entry in entries])
        if sum(entry.file_size for entry in entries) > MAX_PACKAGE:
            raise ValueError("Expanded plugin package exceeds 16 MiB")
        for entry in entries:
            mode = entry.external_attr >> 16
            if entry.is_dir() or stat.S_IFMT(mode) not in (0, stat.S_IFREG) or entry.flag_bits & 1:
                raise ValueError("Plugin package entries must be unencrypted regular files")
        if any(name not in archive.NameToInfo for name in names):
            raise ValueError("A requested file is absent from the plugin package")
        for name in names:
            if any(
                part.endswith((".", " ")) or any(char in part for char in '<>"|?*')
                or re.fullmatch(r"(?i:con|prn|aux|nul|com[0-9¹²³]|lpt[0-9¹²³])", part.split(".")[0].rstrip())
                for part in name.split("/")
            ):
                raise ValueError("Requested file uses a non-portable path")
        with tempfile.TemporaryDirectory(dir=output.parent, prefix=".arrumo-stage-") as temporary:
            pending = Path(temporary) / "package"
            pending.mkdir()
            for name in names:
                path = pending.joinpath(*name.split("/"))
                path.parent.mkdir(parents=True, exist_ok=True)
                with path.open("xb") as target:
                    target.write(archive.read(name))
            pending.rename(output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--include", action="append", required=True, metavar="PATH")
    args = parser.parse_args()
    try:
        stage_files(args.package, args.sha256, args.output, args.include)
    except (OSError, ValueError, RuntimeError, NotImplementedError, zipfile.BadZipFile) as error:
        parser.exit(1, f"{error}\n")


if __name__ == "__main__":
    main()
