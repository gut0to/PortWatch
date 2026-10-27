import json
from datetime import UTC, datetime

import pytest

from portwatch.services.history import decode_history


def record(second, port=3000):
    return json.dumps(
        {
            "scanned_at": f"2026-10-27T12:00:{second:02d}+00:00",
            "ports": []
            if port is None
            else [{"port": port, "protocol": "tcp", "status": "LISTENING", "pid": 42}],
        }
    )


def test_history_decoder_preserves_every_frame():
    frames = decode_history(record(0) + "\n\n" + record(1, None))
    assert len(frames) == 2 and frames[0].ports[0].port == 3000
    assert frames[0].scanned_at == datetime(2026, 10, 27, 12, tzinfo=UTC)
    assert frames[1].ports == ()
    assert decode_history("") == []


@pytest.mark.parametrize(
    "value",
    [
        "{}",
        "[]",
        '{"scanned_at":"2026-01-01","ports":[]}',
        record(0).replace('"pid": 42', '"pid": -1'),
    ],
)
def test_history_reports_the_invalid_record_number(value):
    with pytest.raises(ValueError, match="History line 2"):
        decode_history(record(0) + "\n" + value)


def test_history_loader_bounds_size_and_rejects_backwards_time(tmp_path, monkeypatch):
    import portwatch.services.history as history

    path = tmp_path / "watch.jsonl"
    path.write_text(record(1) + "\n" + record(0))
    with pytest.raises(ValueError, match="chronological"):
        history.load_history(path)
    path.write_text(record(0) + "\n" + record(0), encoding="utf-8-sig")
    assert len(history.load_history(path)) == 2
    monkeypatch.setattr(history, "MAX_HISTORY_BYTES", 1)
    with pytest.raises(ValueError, match="10 MiB"):
        history.load_history(path)


def test_history_summary_counts_transitions_and_empty_histories():
    from portwatch.services.history import summarize_history

    result = summarize_history(
        decode_history(record(0) + "\n" + record(2, 4000) + "\n" + record(3, None))
    )
    assert result == {
        "scans": 3,
        "duration_seconds": 3.0,
        "peak_listeners": 1,
        "unique_ports": 2,
        "added": 1,
        "removed": 2,
        "changed": 0,
    }
    assert summarize_history([])["scans"] == 0


def test_history_command_never_scans_live_machine(tmp_path, monkeypatch):
    from unittest.mock import Mock

    from typer.testing import CliRunner

    import portwatch.cli as cli

    path = tmp_path / "watch.jsonl"
    path.write_text(record(0) + "\n" + record(2, None))
    scan = Mock(side_effect=AssertionError("no live scan"))
    monkeypatch.setattr(cli.service, "list_ports", scan)
    result = CliRunner().invoke(cli.app, ["history", str(path), "--json"])
    assert result.exit_code == 0 and json.loads(result.stdout)["removed"] == 1
    assert "scans: 2" in CliRunner().invoke(cli.app, ["history", str(path)]).stdout
    path.write_text("bad")
    assert CliRunner().invoke(cli.app, ["history", str(path)]).exit_code == 2
    scan.assert_not_called()


def test_history_port_filters_preserve_empty_frames(tmp_path):
    from typer.testing import CliRunner

    import portwatch.cli as cli

    path = tmp_path / "watch.jsonl"
    path.write_text(record(0) + "\n" + record(2, 4000))
    result = CliRunner().invoke(
        cli.app, ["history", str(path), "--ports", "3000-4000", "--exclude", "4000", "--json"]
    )
    assert result.exit_code == 0
    assert json.loads(result.stdout)["scans"] == 2
    assert json.loads(result.stdout)["unique_ports"] == 1


def test_history_metadata_and_pid_filters(tmp_path):
    from typer.testing import CliRunner

    import portwatch.cli as cli

    path = tmp_path / "watch.jsonl"
    path.write_text(record(0))
    result = CliRunner().invoke(
        cli.app, ["history", str(path), "--search", "3000 -4000", "--pid", "42", "--json"]
    )
    assert json.loads(result.stdout)["peak_listeners"] == 1


def test_history_time_window_is_inclusive(tmp_path):
    from typer.testing import CliRunner

    import portwatch.cli as cli

    path = tmp_path / "watch.jsonl"
    path.write_text(record(0) + "\n" + record(2) + "\n" + record(4))
    runner = CliRunner()
    args = [
        "history",
        str(path),
        "--since",
        "2026-10-27T12:00:02Z",
        "--until",
        "2026-10-27T12:00:04Z",
        "--json",
    ]
    assert json.loads(runner.invoke(cli.app, args).stdout)["scans"] == 2
    assert (
        runner.invoke(
            cli.app,
            [
                "history",
                str(path),
                "--since",
                "2026-10-28T00:00:00Z",
                "--until",
                "2026-10-27T00:00:00Z",
            ],
        ).exit_code
        == 2
    )
