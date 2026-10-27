"""Analyze timestamped watch logs without requiring a live scanner."""

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

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
