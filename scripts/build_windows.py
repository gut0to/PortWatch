"""Build and verify the standalone Windows executable."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import struct
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXECUTABLE = PROJECT_ROOT / "dist" / "portwatch.exe"


def _write_checksum(executable: Path) -> Path:
    digest = hashlib.sha256()
    with executable.open("rb") as executable_file:
        for chunk in iter(lambda: executable_file.read(1024 * 1024), b""):
            digest.update(chunk)

    checksum_path = executable.with_suffix(".exe.sha256")
    checksum_path.write_text(f"{digest.hexdigest()}  {executable.name}\n", encoding="ascii")
    return checksum_path


def main(output_directory: Path | None = None) -> None:
    if sys.platform != "win32":
        raise SystemExit("The standalone executable must be built on Windows.")
    if struct.calcsize("P") != 8 or platform.machine().casefold() not in {"amd64", "x86_64"}:
        raise SystemExit("The standalone executable must be built with 64-bit Python.")

    executable = (output_directory.resolve() / "portwatch.exe") if output_directory else EXECUTABLE

    subprocess.run(
        [
            sys.executable,
            "-m",
            "PyInstaller",
            "--clean",
            "--noconfirm",
            "--distpath",
            str(executable.parent),
            "portwatch.spec",
        ],
        cwd=PROJECT_ROOT,
        check=True,
    )

    if not executable.is_file():
        raise SystemExit(f"PyInstaller did not create the expected file: {executable}")

    subprocess.run([str(executable), "--version"], cwd=PROJECT_ROOT, check=True, timeout=30)
    subprocess.run([str(executable), "--help"], cwd=PROJECT_ROOT, check=True, timeout=30)
    port_list = subprocess.run(
        [str(executable), "list", "--json"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        check=True,
        text=True,
        timeout=30,
    )
    json.loads(port_list.stdout)

    subprocess.run(
        [
            sys.executable,
            str(PROJECT_ROOT / "scripts" / "smoke_runtime.py"),
            "--executable",
            str(executable),
        ],
        cwd=PROJECT_ROOT,
        check=True,
        timeout=120,
    )

    checksum_path = _write_checksum(executable)
    print(f"Executable: {executable}")
    print(f"Checksum: {checksum_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir", type=Path, help="Build without replacing an executable in use."
    )
    main(parser.parse_args().output_dir)
