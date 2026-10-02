# Changelog

## [0.1.1] - 2026-10-02

### Fixed

- Opening the Windows executable without arguments starts the dashboard and keeps it running.
- Dashboard confirmation no longer fails with an undefined JavaScript helper.
- Bundled JavaScript and CSS use reliable MIME types independent of the Windows registry.
- CLI errors use stderr and the documented codes for missing ports, permission failures,
  exhausted ports, and failed termination.
- CLI termination rechecks the listener after confirmation and refuses to terminate PortWatch itself.
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
