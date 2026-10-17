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
