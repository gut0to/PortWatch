import json
from datetime import datetime

import pytest
from typer.testing import CliRunner

import portwatch.cli as cli
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


def test_snapshot_diff_detects_restart_and_orders_ports():
    from portwatch.services.snapshots import diff_snapshots

    old = PortInfo(3000, "tcp", "LISTENING", pid=42, started_at=datetime(2026, 1, 1))
    new = PortInfo(3000, "tcp", "LISTENING", pid=42, started_at=datetime(2026, 1, 2))
    result = diff_snapshots([old], [new, PortInfo(80, "tcp", "LISTENING")])
    assert [row["port"] for row in result["added"]] == [80, 3000]
    assert result["removed"] == [port_to_dict(old)]
    assert diff_snapshots([old], [old]) == {"added": [], "removed": [], "changed": []}


def test_snapshot_diff_reports_metadata_changes_without_owner_changes():
    from dataclasses import replace

    from portwatch.services.snapshots import diff_snapshots

    old = PortInfo(3000, "tcp", "LISTENING", pid=42)
    new = replace(old, project_name="API")
    result = diff_snapshots([old], [new])
    assert result["added"] == result["removed"] == []
    assert result["changed"] == [{"before": port_to_dict(old), "after": port_to_dict(new)}]


def test_diff_command_saved_and_live(tmp_path, monkeypatch):
    before = tmp_path / "before.json"
    after = tmp_path / "after.json"
    before.write_text("[]", encoding="utf-8")
    item = PortInfo(3000, "tcp", "LISTENING")
    after.write_text(json.dumps([port_to_dict(item)]), encoding="utf-8")
    monkeypatch.setattr(cli.service, "list_ports", lambda: [item])
    runner = CliRunner()
    saved = runner.invoke(cli.app, ["diff", str(before), str(after), "--json"])
    assert saved.exit_code == 0
    assert json.loads(saved.stdout)["added"] == [port_to_dict(item)]
    live = runner.invoke(cli.app, ["diff", str(before)])
    assert live.exit_code == 0
    assert "Added: 1" in live.stdout
    before.write_text("{}", encoding="utf-8")
    assert runner.invoke(cli.app, ["diff", str(before)]).exit_code == 2
