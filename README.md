# PortWatch

Find out what's using your ports without memorizing `netstat`, `lsof` or `ss`.

## Install

```bash
pip install portwatch
```

## Windows executable

The standalone Windows x64 build is a single `portwatch.exe` file and does not
require Python to be installed on the target machine. Download the
`portwatch-windows-x64` artifact from the latest successful **Windows
executable** workflow run in GitHub Actions. Versioned releases also include
the executable as a downloadable release asset.
Workflow artifacts are retained for 14 days; release assets remain attached to
their versioned release.

Each build includes a SHA-256 checksum file. In PowerShell, calculate the
downloaded file's hash and compare it with the value in the checksum file:

```powershell
Get-FileHash .\portwatch.exe -Algorithm SHA256
Get-Content .\portwatch.exe.sha256
```

To build it locally, use 64-bit Windows with 64-bit Python 3.11 or newer:

```powershell
python -m pip install ".[bundle]"
python scripts/build_windows.py
```

The executable is written to `dist\portwatch.exe`. You can run it from a
terminal or add its containing folder to `PATH`. For example, in PowerShell:

```powershell
dist\portwatch.exe --help
dist\portwatch.exe inspect 3000
```

The same commands are available from the executable:

```powershell
dist\portwatch.exe list
dist\portwatch.exe list --json
dist\portwatch.exe inspect 3000
dist\portwatch.exe next 3000
dist\portwatch.exe watch
```

## Quick start

```bash
portwatch
portwatch inspect 3000
portwatch next 3000
portwatch free 3000
portwatch watch
```

Use `portwatch list --json` or `portwatch inspect 3000 --json` in scripts.

Human-readable commands use Rich formatting; JSON commands write only data to
stdout. Errors are written to stderr with stable exit codes: `0` success, `1`
generic error, `2` invalid arguments, `3` requested port is not listening, `4`
permission denied, and `5` process termination failed.

PortWatch supports Python 3.11+ on Windows and Linux. It is local-first and
does not send telemetry or require an account.

## Roadmap

Docker inspection, UDP support, richer process trees, and a TUI are planned
after the MVP stabilizes.

## License

MIT.
