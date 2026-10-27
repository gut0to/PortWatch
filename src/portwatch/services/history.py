"""Analyze timestamped watch logs without requiring a live scanner."""

import csv
import io
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from portwatch.domain.models import PortInfo
from portwatch.services.reports import summarize_ports
from portwatch.services.snapshots import decode_snapshot, diff_snapshots, parse_snapshot_json


@dataclass(frozen=True, slots=True)
class SnapshotFrame:
    scanned_at: datetime
    ports: tuple[PortInfo, ...]


def parse_history_time(value: str) -> datetime:
    timestamp = datetime.fromisoformat(value)
    if timestamp.tzinfo is None:
        raise ValueError("History timestamps require a timezone offset.")
    return timestamp.astimezone(UTC)


def decode_history(text: str) -> list[SnapshotFrame]:
    frames: list[SnapshotFrame] = []
    for index, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        try:
            data = parse_snapshot_json(line)
            if not isinstance(data, dict) or not isinstance(data.get("scanned_at"), str):
                raise ValueError("History records require scanned_at and ports.")
            timestamp = parse_history_time(data["scanned_at"])
            frames.append(SnapshotFrame(timestamp, tuple(decode_snapshot(data))))
        except ValueError as error:
            raise ValueError(f"History line {index}: {error}") from error
    return frames


MAX_HISTORY_BYTES = 10 * 1024 * 1024


def load_history(path: Path) -> list[SnapshotFrame]:
    with path.open("rb") as source:
        raw = source.read(MAX_HISTORY_BYTES + 1)
    if len(raw) > MAX_HISTORY_BYTES:
        raise ValueError("Watch histories must be at most 10 MiB.")
    frames = decode_history(raw.decode("utf-8-sig"))
    if any(
        current.scanned_at < previous.scanned_at
        for previous, current in zip(frames, frames[1:], strict=False)
    ):
        raise ValueError("History timestamps must be in chronological order.")
    return frames


def summarize_history(frames: list[SnapshotFrame]) -> dict[str, int | float]:
    changes = [
        diff_snapshots(list(a.ports), list(b.ports))
        for a, b in zip(frames, frames[1:], strict=False)
    ]
    return {
        "scans": len(frames),
        "duration_seconds": (frames[-1].scanned_at - frames[0].scanned_at).total_seconds()
        if frames
        else 0.0,
        "peak_listeners": max((len(frame.ports) for frame in frames), default=0),
        "unique_ports": len({item.port for frame in frames for item in frame.ports}),
        "added": sum(len(change["added"]) for change in changes),
        "removed": sum(len(change["removed"]) for change in changes),
        "changed": sum(len(change["changed"]) for change in changes),
    }


def history_events(frames: list[SnapshotFrame]) -> list[dict[str, object]]:
    events: list[dict[str, object]] = []
    for previous, current in zip(frames, frames[1:], strict=False):
        changes = diff_snapshots(list(previous.ports), list(current.ports))
        if any(changes.values()):
            events.append({"scanned_at": current.scanned_at.isoformat(), **changes})
    return events


def history_to_csv(frames: list[SnapshotFrame]) -> str:
    output = io.StringIO(newline="")
    fields = ["scanned_at", "listeners", "ports", "processes", "projects", "unresolved"]
    writer = csv.DictWriter(output, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    for frame in frames:
        writer.writerow(
            {"scanned_at": frame.scanned_at.isoformat(), **summarize_ports(list(frame.ports))}
        )
    return output.getvalue().rstrip("\n")
