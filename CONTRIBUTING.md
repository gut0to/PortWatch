# Contributing

1. Clone the repository and create a Python 3.11+ virtual environment.
2. Install development dependencies with `pip install -e ".[dev]"`.
3. Run the CLI with `portwatch --help`.
4. Run `ruff check .`, `ruff format --check .`, `mypy src`, and `pytest`.
5. Create a focused branch using `feat/`, `fix/`, `test/`, `docs/`, or `ci/`.
6. Use Conventional Commits and describe testing in the pull request.

Please keep changes small, cross-platform, and local-first.

## Build the Windows executable

Use 64-bit Windows and Python 3.11 or newer. Install the bundling extra with
`python -m pip install ".[bundle]"`, then run
`python scripts/build_windows.py`. The helper builds the single-file executable,
checks its CLI entry points, and writes a SHA-256 checksum beside it.
