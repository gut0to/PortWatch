"""Validate portable listener snapshots and compare their process identities."""

import json
from datetime import datetime
from pathlib import Path
from typing import cast

from portwatch.domain.models import PortInfo
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
    return decode_snapshot(json.loads(raw.decode("utf-8")))
