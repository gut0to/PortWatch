"""Build and verify the standalone Windows executable."""

from __future__ import annotations

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


def main() -> None:
    if sys.platform != "win32":
        raise SystemExit("The standalone executable must be built on Windows.")
    if struct.calcsize("P") != 8 or platform.machine().casefold() not in {"amd64", "x86_64"}:
        raise SystemExit("The standalone executable must be built with 64-bit Python.")

    subprocess.run(
        [sys.executable, "-m", "PyInstaller", "--clean", "--noconfirm", "portwatch.spec"],
        cwd=PROJECT_ROOT,
        check=True,
    )

    if not EXECUTABLE.is_file():
        raise SystemExit(f"PyInstaller did not create the expected file: {EXECUTABLE}")

    subprocess.run([str(EXECUTABLE), "--version"], cwd=PROJECT_ROOT, check=True, timeout=30)
    subprocess.run([str(EXECUTABLE), "--help"], cwd=PROJECT_ROOT, check=True, timeout=30)
    port_list = subprocess.run(
        [str(EXECUTABLE), "list", "--json"],
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
            str(EXECUTABLE),
        ],
        cwd=PROJECT_ROOT,
        check=True,
        timeout=120,
    )

    checksum_path = _write_checksum(EXECUTABLE)
    print(f"Executable: {EXECUTABLE}")
    print(f"Checksum: {checksum_path}")


if __name__ == "__main__":
    main()
