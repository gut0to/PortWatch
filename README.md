# PortWatch

Find out what's using your ports without memorizing `netstat`, `lsof` or `ss`.

## Install

```bash
pip install portwatch
```

For a checkout on Windows, use Python 3.11 or newer in a virtual environment:

```powershell
py -3 -m venv .venv
.venv\Scripts\python.exe -m pip install -e ".[dev,bundle]"
.\run.ps1 --version
.\run.ps1 dashboard --no-browser
```

Check `py -3 --version` before creating the environment. Python 3.10 is unsupported.
The launcher uses `.venv` explicitly, so an older global Python does not interfere.

## Windows executable

The standalone Windows x64 build is a single `portwatch.exe` file and does not
require Python to be installed on the target machine. Download the
`portwatch-windows-x64` artifact from the latest successful **Windows
executable** workflow run in GitHub Actions. Versioned releases also include
the executable as a downloadable release asset.
Workflow artifacts are retained for 14 days; release assets remain attached to
their versioned release. Pushing a tag whose name starts with `v` starts the
release build and attaches both the executable and checksum.

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

If `dist\portwatch.exe` is already in use, build into a separate directory:

```powershell
.venv\Scripts\python.exe scripts/build_windows.py --output-dir dist\release-0.1.1
```

The build verifies the CLI, live port discovery, bundled dashboard assets and a
confirmed termination using a disposable test process. It does not open a browser.

The executable and its checksum are written to `dist\portwatch.exe` and
`dist\portwatch.exe.sha256`. Double-click the executable to start the local
dashboard. Keep its console window open while using the dashboard; press Ctrl+C
in that window to stop it. If the browser does not open, use the printed local URL.
Launching the executable without arguments from a terminal also starts the dashboard.
Use the explicit `list` command to print a port list and exit.
You can run it from a terminal or add its
containing folder to `PATH`. For example, in PowerShell:

```powershell
dist\portwatch.exe --help
dist\portwatch.exe --version
dist\portwatch.exe inspect 3000
```

The same commands are available from the executable:

```powershell
dist\portwatch.exe list
dist\portwatch.exe list --json
dist\portwatch.exe inspect 3000
dist\portwatch.exe next 3000
dist\portwatch.exe watch
dist\portwatch.exe free 3000
dist\portwatch.exe dashboard
```

The `free` command asks before terminating a process. Pass `--yes` only when
you want to skip that confirmation.

## Quick start

```bash
portwatch
portwatch inspect 3000
portwatch next 3000
portwatch free 3000
portwatch watch
portwatch dashboard
```

`dashboard` opens a local browser view of listening TCP ports, their owning
processes, and detected project directories. It binds only to `127.0.0.1`; no
account or telemetry is used. The dashboard asks for confirmation before it
requests that a process stop. Use `portwatch dashboard --no-browser` to print
the local URL without opening a tab, or `--port 4100` to choose a fixed local
port instead of an available one.

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
