# Changelog

## Unreleased

### Snapshot interoperability and inspection

- Import UTF-8 BOM files, JSON Lines, dashboard responses, and the latest watch-log snapshot.
- Reject ambiguous imported fields and duplicate listeners; normalize equivalent timestamp offsets.
- Filter, redact, and export snapshot differences to JSON or spreadsheet-safe CSV.
- Apply consistent port and ownership filters to summaries and watch sessions.
- Sort grouped summaries, save reports, and exclude reserved ports from free-port discovery.
- Persist flushed monitoring logs and support baseline-only startup.
- Inspect all owners of a port, reuse per-scan project detection, and diagnose the local runtime.
- Refresh the standalone Windows executable and its checksum.

### Snapshot and monitoring improvements

- Select or exclude disjoint port ranges; combine search terms and exclusions.
- Add exact process/project matching, pagination, quiet/count output, and JSON Lines.
- Add summaries with process/project groups and validated snapshot comparison.
- Save complete UTF-8 snapshots with explicit overwrite and optional metadata redaction.
- Clean temporary exports after write/close failures and keep empty JSON Lines files empty.
- Add snapshot-difference exit status 6, bounded free-port batches, and JSON watch streams.
- Suppress unchanged watch snapshots and apply shared metadata filters to monitoring.
- Preserve literal names and command argument boundaries in process presentation.
- Handle timezone-aware and invalid timestamps and malformed socket owners safely.
- Neutralize spreadsheet formulas in CSV metadata.
- Support HEAD requests and reject ambiguous framing and non-finite action JSON.


### Added

- CLI listener search and combined PID, process, and project filters.
- Sorting by port, PID, process, or project with optional descending order.
- CSV listener snapshots, JSON available-port discovery, and bounded watch sessions.
- Project detection for Kotlin Gradle, Deno, CMake, Make, and .NET.

### Fixed

- Range filtering and single-port queries avoid reading unrelated process metadata.
- Available-port discovery reads the socket inventory without process enrichment.
- TCP scans no longer collect UDP sockets and tolerate malformed socket addresses.
- Port validation rejects non-integers, Unicode digits, and oversized range values.
- Version requests exit before running a subcommand; watch intervals reject infinity and NaN.
- Dashboard requests bound query fields, reject duplicate JSON keys, and time out idle sockets.
- Dashboard termination rechecks process start time to detect PID reuse.
- Dashboard snapshots are validated before replacing visible results.
- Repeated stop submissions are ignored and confirmations are blocked during scans.
- Rescan recovers initial session failures; action feedback survives follow-up scans.

## [0.1.1] - 2026-10-02

### Fixed

- Opening the Windows executable without arguments starts the dashboard and keeps it running.
- Dashboard confirmation no longer fails with an undefined JavaScript helper.
- Bundled JavaScript and CSS use reliable MIME types independent of the Windows registry.
- CLI errors use stderr and the documented codes for missing ports, permission failures,
  exhausted ports, and failed termination.
- CLI termination rechecks the listener after confirmation and refuses to terminate PortWatch itself.
- Linux processes awaiting parent reaping are recognized as exited instead of timing out as zombies.
- Empty dashboard ranges and malformed action tokens are rejected explicitly.

### Changed

- Windows builds verify real listeners, bundled HTTP assets, and confirmed termination before
  producing the executable checksum.
- CI runs JavaScript regressions and a live runtime smoke on Windows and Linux.
- A Windows launcher selects the project's supported virtual environment.

## [0.1.0] - Unreleased

### Added

- A standalone Windows x64 executable with a SHA-256 checksum in workflow artifacts and tagged releases.
- Cross-platform listening port discovery.
- Process metadata and project-root detection.
- `list`, `inspect`, `next`, `kill`, `free`, and `watch` commands.
- JSON output for list and inspect.
