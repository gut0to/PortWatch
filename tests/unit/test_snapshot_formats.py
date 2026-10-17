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

    first = PortInfo(3000, "tcp", "LISTENING", pid=42, started_at=datetime(2026, 1, 1, tzinfo=UTC))
    second = replace(first, started_at=first.started_at.astimezone(timezone(timedelta(hours=-3))))
    assert not any(diff_snapshots([first], [second]).values())


def test_json_lines_decode_blank_lines_and_report_bad_lines():
    from portwatch.services.snapshots import decode_json_lines

    row = '{"port":3000,"protocol":"tcp","status":"LISTENING"}'
    assert decode_json_lines("\n" + row + "\n\n")[0].port == 3000
    assert decode_json_lines("") == []
    with pytest.raises(ValueError, match="line 2"):
        decode_json_lines(row + "\nbad")


@pytest.mark.parametrize("extension", ["jsonl", "ndjson", "JSONL"])
def test_snapshot_file_format_follows_extension(tmp_path, extension):
    path = tmp_path / f"ports.{extension}"
    path.write_text('{"port":3000,"protocol":"tcp","status":"LISTENING"}\n')
    assert load_snapshot(path)[0].port == 3000


def test_import_dashboard_snapshots_and_latest_watch_record(tmp_path):
    from portwatch.services.snapshots import decode_json_lines, decode_snapshot

    row = {"port": 3000, "protocol": "tcp", "status": "LISTENING"}
    assert decode_snapshot({"ports": [row], "scanned_at": "2026-01-01"})[0].port == 3000
    assert (
        decode_json_lines('{"ports":[]}\n' + __import__("json").dumps({"ports": [row]}))[0].port
        == 3000
    )
    assert decode_json_lines('{"ports":["bad"]}\n{"ports":[]}') == []
    with pytest.raises(ValueError):
        decode_snapshot({"ports": "bad"})


def test_ignored_diff_fields_do_not_hide_identity_changes():
    from dataclasses import replace

    from portwatch.domain.models import PortInfo
    from portwatch.services.snapshots import diff_snapshots

    first = PortInfo(3000, "tcp", "LISTENING", pid=42, command="old")
    assert not any(
        diff_snapshots(
            [first], [replace(first, command="new")], ignore_fields=frozenset({"command"})
        ).values()
    )
    assert diff_snapshots([first], [replace(first, pid=43)], ignore_fields=frozenset({"command"}))[
        "added"
    ]
    with pytest.raises(ValueError, match="Only"):
        diff_snapshots([], [], ignore_fields=frozenset({"pid"}))
