from datetime import datetime

import pytest

from portwatch.domain.models import PortInfo
from portwatch.presentation.serializers import port_to_dict
from portwatch.services.snapshots import decode_snapshot


def test_snapshot_round_trip_with_optional_metadata():
    item = PortInfo(
        3000, "tcp", "LISTENING", pid=42, command="server", started_at=datetime(2026, 1, 1)
    )
    assert decode_snapshot([port_to_dict(item)]) == [item]
    assert decode_snapshot([]) == []
    assert decode_snapshot([{"port": 1, "protocol": "tcp", "status": "LISTENING"}])[0].pid is None


@pytest.mark.parametrize(
    "data",
    [
        None,
        {},
        [1],
        [{}],
        [{"port": True, "protocol": "tcp", "status": "LISTENING"}],
        [{"port": 1, "protocol": "udp", "status": "LISTENING"}],
        [{"port": 1, "protocol": "tcp", "status": "LISTENING", "pid": -1}],
        [{"port": 1, "protocol": "tcp", "status": "LISTENING", "command": 3}],
        [{"port": 1, "protocol": "tcp", "status": "LISTENING", "extra": 3}],
        [{"port": 1, "protocol": "tcp", "status": "LISTENING", "started_at": "bad"}],
    ],
)
def test_snapshot_rejects_invalid_schema(data):
    with pytest.raises(ValueError):
        decode_snapshot(data)


def test_snapshot_file_loader_bounds_reads_and_validates_json(tmp_path, monkeypatch):
    import portwatch.services.snapshots as snapshots

    path = tmp_path / "ports.json"
    path.write_text("[]", encoding="utf-8")
    assert snapshots.load_snapshot(path) == []
    monkeypatch.setattr(snapshots, "MAX_SNAPSHOT_BYTES", 2)
    path.write_bytes(b"[] ")
    with pytest.raises(ValueError, match="10 MiB"):
        snapshots.load_snapshot(path)
    path.write_bytes(b"\xff")
    with pytest.raises(ValueError):
        snapshots.load_snapshot(path)
    path.write_text("{", encoding="utf-8")
    with pytest.raises(ValueError):
        snapshots.load_snapshot(path)
