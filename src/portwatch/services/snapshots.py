"""Validate portable listener snapshots and compare their process identities."""

import json
import os
import tempfile
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from typing import cast

from portwatch.domain.models import PortInfo
from portwatch.presentation.serializers import port_to_dict
from portwatch.utils.ports import validate_port


def decode_snapshot(data: object) -> list[PortInfo]:
    if not isinstance(data, list):
        raise ValueError("A snapshot must be a JSON array of listeners.")
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
    return ports


MAX_SNAPSHOT_BYTES = 10 * 1024 * 1024


def load_snapshot(path: Path) -> list[PortInfo]:
    with path.open("rb") as source:
        raw = source.read(MAX_SNAPSHOT_BYTES + 1)
    if len(raw) > MAX_SNAPSHOT_BYTES:
        raise ValueError("Snapshot files must be at most 10 MiB.")
    return decode_snapshot(json.loads(raw.decode("utf-8-sig"), object_pairs_hook=_unique_fields))


def _identity(item: PortInfo) -> tuple[int, str, int, str]:
    return (
        item.port,
        item.protocol,
        item.pid or -1,
        item.started_at.isoformat() if item.started_at else "",
    )


def diff_snapshots(
    before: list[PortInfo], after: list[PortInfo]
) -> dict[str, list[dict[str, object]]]:
    previous = {_identity(item): item for item in before}
    current = {_identity(item): item for item in after}
    return {
        "added": [port_to_dict(current[key]) for key in sorted(current.keys() - previous.keys())],
        "changed": [
            {"before": port_to_dict(previous[key]), "after": port_to_dict(current[key])}
            for key in sorted(previous.keys() & current.keys())
            if previous[key] != current[key]
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
