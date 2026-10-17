import json
from unittest.mock import Mock

import pytest
from typer.testing import CliRunner

import portwatch.cli as cli
from portwatch.domain.models import PortInfo


@pytest.fixture
def listeners(monkeypatch):
    items = [
        PortInfo(
            3000,
            "tcp",
            "LISTENING",
            pid=42,
            process_name="python",
            command="secret",
            working_directory="private",
        ),
        PortInfo(3001, "tcp", "LISTENING", pid=42, process_name="python-worker"),
    ]
    monkeypatch.setattr(cli.service, "list_ports", lambda bounds=None: items)
    monkeypatch.setattr(cli.time, "sleep", Mock())
    return items


def invoke(*args):
    return CliRunner().invoke(cli.app, ["watch", "--count", "2", *args])


def test_watch_disjoint_ports_and_exclusions(listeners):
    result = invoke("--ports", "3000-3001", "--exclude", "3001", "--json")
    assert result.exit_code == 0
    assert [item["port"] for item in json.loads(result.stdout.splitlines()[0])["ports"]] == [3000]
    assert invoke("--ports", "bad").exit_code == 2


def test_watch_redaction_does_not_modify_source_records(listeners):
    result = invoke("--redact", "--json")
    assert result.exit_code == 0
    assert "secret" not in result.stdout and "private" not in result.stdout
    assert json.loads(result.stdout.splitlines()[0])["ports"][0]["command"] is None
    assert listeners[0].command == "secret"
    assert invoke("--redact").exit_code == 0


def test_watch_file_log_round_trips_and_never_overwrites(listeners, tmp_path):
    from portwatch.services.snapshots import load_snapshot

    path = tmp_path / "watch.jsonl"
    result = invoke("--output", str(path), "--redact")
    assert result.exit_code == 0 and result.stdout == ""
    assert len(path.read_text().splitlines()) == 2
    assert load_snapshot(path)[0].command is None
    before = path.read_bytes()
    assert invoke("--output", str(path)).exit_code == 2
    assert path.read_bytes() == before


def test_watch_exact_process_filter(listeners):
    result = invoke("--process", "PYTHON", "--exact", "--json")
    assert result.exit_code == 0
    assert [item["port"] for item in json.loads(result.stdout.splitlines()[0])["ports"]] == [3000]
