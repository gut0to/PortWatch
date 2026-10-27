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

Narrow a listener snapshot by range, search text, process ID, process name, or
detected project name. Text filters ignore case and combine with each other:

```bash
portwatch list --range 3000-9000 --search backend
portwatch list --process python --project backend --json
portwatch list --pid 1234 --csv
portwatch list --sort process --descending
portwatch next 3000 --json
portwatch watch --interval 1 --count 10
```

`--sort` accepts `port` (the default), `pid`, `process`, and `project`.
`--csv` includes a header even when no listeners match; choose either `--csv`
or `--json`. `next --json` returns `start`, `port`, and `available`, where
`available` indicates whether the starting port was free in the scan.
Available-port discovery is a snapshot; it does not reserve a socket.
`watch --count N` stops after N scans; omitting it or using zero watches until
Ctrl+C. Intervals must be finite and at least 0.2 seconds.

Project detection recognizes Kotlin Gradle, Deno, CMake, Make, and .NET project
and solution files alongside the existing project markers.

The dashboard retains the previous results if a scan returns invalid data and
can reconnect through Rescan after an initial connection failure. Stopping a
process rechecks its PID and start time against the confirmed listener. A
restarted process requires a fresh scan and confirmation.

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


### Targeted listener queries

`list --ports 80,443,3000-3010 --exclude 3005` selects disjoint ports and ranges.
`--search "python api -worker"` requires every positive term and excludes metadata
containing `worker`. Process and project filters support `--exact` for full-name
matching. All matching is case-insensitive.

Use `--offset N --limit N` to paginate after sorting. `--quiet` prints unique port
numbers; `--count` prints the number of listener records (owners sharing a port
are separate records). `--json-lines` emits one listener object per line and no
output for an empty result. These formats cannot be combined with each other,
`--json`, or `--csv`.


### Listener summaries

`portwatch summary` reports listener records, unique ports, process IDs, detected
project names, and unresolved owners. Add `--json` for scripts, `--range` or
`--search` to narrow the snapshot, and `--group process` or `--group project` for
per-name totals. Missing names appear in the `Unknown` group.


### Comparing snapshots

Save `portwatch list --json` to a UTF-8 file, then run
`portwatch diff before.json after.json --json`. Omit the second file to compare
the saved snapshot with a live scan. Added and removed records include process
start time in their identity, so a restart is visible even if a PID is reused.
Changed records show before/after metadata for an existing owner.

`diff --exit-code` returns 6 when differences exist and 0 when unchanged; JSON
output is still written on differences. Invalid snapshots return 2. Input files
must contain a JSON array of listening TCP records and be at most 10 MiB.


`portwatch list --output ports.json` writes a complete UTF-8 JSON snapshot
without emitting a table. Select `--csv` or `--json-lines` for those file formats.
The parent directory must exist. Existing files are preserved unless you pass
`--overwrite`; publication uses a temporary file in the destination directory.


Add `list --redact` to remove command lines and working-directory paths from
the resulting output. Filtering uses the original metadata first. Process names,
project names, PIDs, and timestamps remain available; review them before sharing.


CSV text fields beginning with spreadsheet formula prefixes are prefixed with
an apostrophe. JSON and JSON Lines preserve their original text.


### Scripted monitoring and free-port batches

`portwatch next 3000 --end 4000 --count 3 --json` finds three free TCP port
numbers in one scan. All requested ports must fit in the inclusive range;
otherwise the command exits with 3. A single-port request retains the existing
`start`, `port`, and `available` JSON fields; batches return `start` and `ports`.
These results do not reserve sockets.

`portwatch watch --json --count 10 --changes-only --search "api -worker"`
streams a JSON object containing `ports` and `scanned_at` for each changed
snapshot. The first snapshot is always emitted, including when empty. `--count`
counts scan attempts, including suppressed duplicates. Reordering alone is not
a change. Watch accepts the same `--pid`, `--process`, and `--project` filters
as listener queries.


### Importing snapshots from other workflows

`diff` accepts UTF-8 files with or without a BOM. Files ending in `.jsonl` or
`.ndjson` are read as JSON Lines; blank lines are ignored. Listener arrays and
dashboard `{ "ports": [...] }` responses are accepted. For a JSON Lines watch
log, the last complete snapshot is used. Invalid final records fail explicitly.
Duplicate JSON fields and listener identities are rejected.


`diff` supports `--ports`, shared `--search` expressions, and repeatable
`--ignore command` / `--ignore working_directory` / `--ignore process_name` /
`--ignore project_name` options. Identity fields cannot be ignored. Use `--csv`
for a report with change and before/after columns, or `--output` to save JSON
by default. Existing reports require `--overwrite`.
`--redact` hides commands and directories after comparison, preserving the
presence of sensitive metadata changes without exposing their values.


`summary` accepts `--ports`, `--exclude`, `--pid`, `--process`, `--project`,
and `--exact` in addition to search and range filtering. Grouped rows can be
sorted with `--sort name|listeners|ports|processes|projects` and `--descending`.
`--output report.json` saves the JSON summary; replacement requires `--overwrite`.


`watch` accepts disjoint `--ports` selections, `--exclude`, `--exact`, and
`--redact`. `--output watch.jsonl` creates a new UTF-8 log and flushes each
snapshot to disk; existing files are never replaced. This output can be read
by `diff`, which uses its latest snapshot. `--skip-initial` establishes the
first scan as a baseline without emitting it, while still counting that scan
toward `--count`. Combine it with `--changes-only` to emit only later changes.
`next --exclude 3000-3010` avoids reserved ports even when they are currently free.


`portwatch inspect 3000 --all` shows every discovered owner of the selected
port. With `--json`, `--all` returns an array; the existing single-owner command
continues to return one object. Project detection reuses working-directory
results only within a scan, so later scans still observe filesystem changes.


`portwatch doctor --json` reports the application, Python, operating system,
architecture, psutil version, and whether the local TCP scan succeeds. It does
not inspect command lines or terminate processes. An unavailable scan returns
1, or 4 for insufficient permissions, while preserving the JSON diagnostic data.


### Analyze saved monitoring history

`portwatch history watch.jsonl --json` reports scan count, duration, listener
peaks, unique ports, and added/removed/changed listener totals. History files
must contain timezone-aware `scanned_at` values in chronological order and be
at most 10 MiB. Empty scans remain part of the timeline.

Use `--ports`, `--exclude`, `--search`, or `--pid` to focus the analysis. `--since`
and `--until` accept inclusive ISO timestamps with timezone offsets. `--events`
adds timestamped transitions; `--csv` instead exports a row of totals per scan.
`--output` saves a report, with explicit `--overwrite` required for replacement.
