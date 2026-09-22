# PortWatch

Find out what's using your ports without memorizing `netstat`, `lsof` or `ss`.

## Install

```bash
pip install portwatch
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
