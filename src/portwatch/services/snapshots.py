"""Validate portable listener snapshots and compare their process identities."""

import csv
import io
import json
import math
import os
import tempfile
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

from portwatch.domain.models import PortInfo
from portwatch.presentation.serializers import port_to_dict
from portwatch.utils.ports import validate_port


def decode_snapshot(data: object) -> list[PortInfo]:
    if isinstance(data, dict) and "ports" in data:
        data = data["ports"]
    if not isinstance(data, list):
        raise ValueError("A snapshot must be a JSON array of listeners.")
    seen: set[tuple[int, str, int, str]] = set()
    ports: list[PortInfo] = []
    for row in data:
        if not isinstance(row, dict) or not {"port", "protocol", "status"} <= row.keys():
            raise ValueError("Each listener requires port, protocol, and status fields.")
        if row.keys() - PortInfo.__dataclass_fields__.keys():
            raise ValueError("A snapshot listener contains unknown fields.")
        port = row["port"]
        if isinstance(port, bool) or not isinstance(port, int):
            raise ValueError("Snapshot ports must be integers.")
        validate_port(port)
        if row["protocol"] != "tcp" or row["status"] != "LISTENING":
            raise ValueError("Snapshots support listening TCP ports only.")
        pid = row.get("pid")
        if pid is not None and (isinstance(pid, bool) or not isinstance(pid, int) or pid <= 0):
            raise ValueError("Snapshot process IDs must be positive integers or null.")
        for field in ("process_name", "command", "working_directory", "project_name", "started_at"):
            if row.get(field) is not None and not isinstance(row[field], str):
                raise ValueError(f"Snapshot {field} must be a string or null.")
        started = row.get("started_at")
        ports.append(
            PortInfo(
                port,
                "tcp",
                "LISTENING",
                pid=pid,
                process_name=cast(str | None, row.get("process_name")),
                command=cast(str | None, row.get("command")),
                working_directory=cast(str | None, row.get("working_directory")),
                project_name=cast(str | None, row.get("project_name")),
                started_at=datetime.fromisoformat(started) if started is not None else None,
            )
        )
        key = _identity(ports[-1])
        if key in seen:
            raise ValueError("Duplicate listener identity in snapshot.")
        seen.add(key)
    return ports


MAX_SNAPSHOT_BYTES = 10 * 1024 * 1024


def load_snapshot(path: Path) -> list[PortInfo]:
    with path.open("rb") as source:
        raw = source.read(MAX_SNAPSHOT_BYTES + 1)
    if len(raw) > MAX_SNAPSHOT_BYTES:
        raise ValueError("Snapshot files must be at most 10 MiB.")
    text = raw.decode("utf-8-sig")
    if path.suffix.casefold() == ".csv":
        return decode_csv_snapshot(text)
    if path.suffix.casefold() in {".jsonl", ".ndjson"}:
        return decode_json_lines(text)
    return decode_snapshot(parse_snapshot_json(text))


def _identity(item: PortInfo) -> tuple[int, str, int, str]:
    return (
        item.port,
        item.protocol,
        item.pid or -1,
        item.started_at.astimezone(UTC).isoformat() if item.started_at else "",
    )


def diff_snapshots(
    before: list[PortInfo], after: list[PortInfo], *, ignore_fields: frozenset[str] = frozenset()
) -> dict[str, list[dict[str, object]]]:
    if ignore_fields - {"command", "working_directory", "process_name", "project_name"}:
        raise ValueError(
            "Only command, working_directory, process_name, and project_name can be ignored."
        )
    previous = {_identity(item): item for item in before}
    current = {_identity(item): item for item in after}
    return {
        "added": [port_to_dict(current[key]) for key in sorted(current.keys() - previous.keys())],
        "changed": [
            {"before": port_to_dict(previous[key]), "after": port_to_dict(current[key])}
            for key in sorted(previous.keys() & current.keys())
            if {
                field: value
                for field, value in port_to_dict(previous[key]).items()
                if field not in ignore_fields and field != "started_at"
            }
            != {
                field: value
                for field, value in port_to_dict(current[key]).items()
                if field not in ignore_fields and field != "started_at"
            }
        ],
        "removed": [
            port_to_dict(previous[key]) for key in sorted(previous.keys() - current.keys())
        ],
    }


def write_snapshot(path: Path, content: str, *, overwrite: bool = False) -> None:
    """Publish a complete UTF-8 snapshot; existing files require explicit replacement."""
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as output:
            temporary = Path(output.name)
            output.write(content + ("\n" if content else ""))
        if overwrite:
            os.replace(temporary, path)
        else:
            os.link(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def redact_snapshot(ports: list[PortInfo]) -> list[PortInfo]:
    """Remove command lines and local paths while retaining comparison identities."""
    return [replace(item, command=None, working_directory=None) for item in ports]


def _unique_fields(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate snapshot field: {key}.")
        result[key] = value
    return result


def decode_json_lines(text: str) -> list[PortInfo]:
    rows: list[object] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            rows.append(parse_snapshot_json(line))
        except ValueError as error:
            raise ValueError(f"Invalid JSON on line {line_number}: {error}") from error
    if rows and all(isinstance(row, dict) and "ports" in row for row in rows):
        return decode_snapshot(rows[-1])
    return decode_snapshot(rows)


def redact_changes(
    changes: dict[str, list[dict[str, object]]],
) -> dict[str, list[dict[str, object]]]:
    def clean(row: dict[str, object]) -> dict[str, object]:
        return {**row, "command": None, "working_directory": None}

    return {
        kind: [
            {
                "before": clean(cast(dict[str, object], row["before"])),
                "after": clean(cast(dict[str, object], row["after"])),
            }
            if kind == "changed"
            else clean(row)
            for row in rows
        ]
        for kind, rows in changes.items()
    }


def _reject_constant(value: str) -> object:
    raise ValueError(f"Non-finite snapshot number: {value}.")


def _finite_float(value: str) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("Snapshot numbers must be finite.")
    return number


def parse_snapshot_json(text: str) -> object:
    try:
        data = json.loads(
            text,
            object_pairs_hook=_unique_fields,
            parse_constant=_reject_constant,
            parse_float=_finite_float,
        )
        pending = [(data, 0)]
        while pending:
            value, depth = pending.pop()
            if depth > 64:
                raise ValueError("Snapshot JSON is nested too deeply.")
            if isinstance(value, list):
                pending.extend((item, depth + 1) for item in value)
            elif isinstance(value, dict):
                pending.extend((item, depth + 1) for item in value.values())
        return data
    except RecursionError as error:
        raise ValueError("Snapshot JSON is nested too deeply.") from error


def decode_csv_snapshot(text: str) -> list[PortInfo]:
    reader = csv.DictReader(io.StringIO(text), strict=True)
    fields = reader.fieldnames
    if (
        fields is None
        or len(fields) != len(set(fields))
        or not {"port", "protocol", "status"} <= set(fields)
    ):
        raise ValueError("CSV snapshots require unique port, protocol, and status columns.")
    if set(fields) - PortInfo.__dataclass_fields__.keys():
        raise ValueError("CSV snapshot contains unknown columns.")
    rows: list[dict[str, object]] = []
    try:
        for row in reader:
            if None in row or any(value is None for value in row.values()):
                raise ValueError("CSV snapshot rows must match their header.")
            converted: dict[str, object] = dict(row)
            for name in ("port", "pid"):
                value = row.get(name, "")
                if name == "pid" and not value:
                    converted[name] = None
                    continue
                if not value.isascii() or not value.isdecimal() or len(value) > 10:
                    raise ValueError(f"CSV {name} must be a decimal integer.")
                converted[name] = int(value)
            for name in (
                "process_name",
                "project_name",
                "command",
                "working_directory",
                "started_at",
            ):
                if name in converted and converted[name] == "":
                    converted[name] = None
            rows.append(converted)
    except csv.Error as error:
        raise ValueError(f"Invalid CSV snapshot: {error}") from error
    return decode_snapshot(rows)
