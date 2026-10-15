import json

import pytest
from typer.testing import CliRunner

import portwatch.cli as cli
from portwatch.domain.models import PortInfo
from portwatch.presentation.serializers import ports_to_json_lines


def test_json_lines_escape_embedded_newlines():
    items = [
        PortInfo(3000, "tcp", "LISTENING", command="one\ntwo"),
        PortInfo(4000, "tcp", "LISTENING"),
    ]
    lines = ports_to_json_lines(items).splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0])["command"] == "one\ntwo"
    assert ports_to_json_lines([]) == ""


@pytest.fixture
def listeners(monkeypatch):
    items = [
        PortInfo(3000, "tcp", "LISTENING", pid=10, process_name="Python", project_name="API"),
        PortInfo(4000, "tcp", "LISTENING", pid=10, process_name="Python", project_name="API"),
        PortInfo(4000, "tcp", "LISTENING"),
    ]
    monkeypatch.setattr(cli.service, "list_ports", lambda port_range=None: items)
    return items


def invoke(*args):
    result = CliRunner().invoke(cli.app, list(args))
    assert result.exit_code == 0, result.output
    return result.stdout
