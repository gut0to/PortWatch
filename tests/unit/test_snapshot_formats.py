from datetime import UTC

import pytest

from portwatch.services.snapshots import load_snapshot


def test_load_utf8_bom_snapshot(tmp_path):
    path = tmp_path / "ports.json"
    path.write_bytes(b"\xef\xbb\xbf[]")
    assert load_snapshot(path) == []


def test_snapshot_json_rejects_duplicate_identity_fields(tmp_path):
    path = tmp_path / "ports.json"
    path.write_text('[{"port":1,"port":2,"protocol":"tcp","status":"LISTENING"}]')
    with pytest.raises(ValueError, match="Duplicate snapshot field"):
        load_snapshot(path)
    path.write_text('[{"port":1,"protocol":"tcp","status":"LISTENING"}]')
    assert load_snapshot(path)[0].port == 1


def test_duplicate_listener_records_cannot_silently_overwrite_each_other():
    from portwatch.domain.models import PortInfo
    from portwatch.presentation.serializers import port_to_dict
    from portwatch.services.snapshots import decode_snapshot

    row = port_to_dict(PortInfo(3000, "tcp", "LISTENING", pid=42))
    with pytest.raises(ValueError, match="Duplicate listener identity"):
        decode_snapshot([row, {**row, "command": "different"}])


def test_equivalent_timestamp_offsets_preserve_listener_identity():
    from dataclasses import replace
    from datetime import datetime, timedelta, timezone

    from portwatch.domain.models import PortInfo
    from portwatch.services.snapshots import diff_snapshots

    first = PortInfo(
        3000, "tcp", "LISTENING", pid=42, started_at=datetime(2026, 1, 1, tzinfo=UTC)
    )
    second = replace(first, started_at=first.started_at.astimezone(timezone(timedelta(hours=-3))))
    assert not any(diff_snapshots([first], [second]).values())
