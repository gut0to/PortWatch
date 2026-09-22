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

PortWatch supports Python 3.11+ on Windows and Linux. It is local-first and
does not send telemetry or require an account.

## Roadmap

Docker inspection, UDP support, richer process trees, and a TUI are planned
after the MVP stabilizes.

## License

MIT.
