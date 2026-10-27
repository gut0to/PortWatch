"""Analyze timestamped watch logs without requiring a live scanner."""

from dataclasses import dataclass
from datetime import UTC, datetime

from portwatch.domain.models import PortInfo
from portwatch.services.snapshots import decode_snapshot, parse_snapshot_json


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
