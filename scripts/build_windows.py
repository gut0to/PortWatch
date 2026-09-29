"""Build and verify the standalone Windows executable."""

from __future__ import annotations

import hashlib
import platform
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXECUTABLE = PROJECT_ROOT / "dist" / "portwatch.exe"


def main() -> None:
    if sys.platform != "win32":
        raise SystemExit("The standalone executable must be built on Windows.")
    if sys.version_info < (3, 11):
        raise SystemExit("The standalone executable requires Python 3.11 or newer.")
    if platform.machine().casefold() not in {"amd64", "x86_64"}:
        raise SystemExit("The standalone executable must be built with 64-bit Python.")

    subprocess.run(
        [sys.executable, "-m", "PyInstaller", "--clean", "--noconfirm", "portwatch.spec"],
        cwd=PROJECT_ROOT,
        check=True,
    )

    if not EXECUTABLE.is_file():
        raise SystemExit(f"PyInstaller did not create the expected file: {EXECUTABLE}")

    subprocess.run([str(EXECUTABLE), "--version"], cwd=PROJECT_ROOT, check=True)
    subprocess.run([str(EXECUTABLE), "--help"], cwd=PROJECT_ROOT, check=True)

    digest = hashlib.sha256()
    with EXECUTABLE.open("rb") as executable_file:
        for chunk in iter(lambda: executable_file.read(1024 * 1024), b""):
            digest.update(chunk)
    checksum = digest.hexdigest()
    checksum_path = EXECUTABLE.with_suffix(".exe.sha256")
    checksum_path.write_text(f"{checksum}  {EXECUTABLE.name}\n", encoding="ascii")
    print(f"Executable: {EXECUTABLE}")
    print(f"Checksum: {checksum_path}")


if __name__ == "__main__":
    main()
