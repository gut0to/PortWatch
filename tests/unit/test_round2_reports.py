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


def test_cli_json_lines(listeners):
    rows = [json.loads(line) for line in invoke("list", "--json-lines").splitlines()]
    assert [item["port"] for item in rows] == [3000, 4000, 4000]
    assert invoke("list", "--json-lines", "--search", "missing") == ""
    assert CliRunner().invoke(cli.app, ["list", "--json-lines", "--json"]).exit_code == 2


def test_summary_distinguishes_unique_ports_and_processes(listeners):
    from portwatch.services.reports import summarize_ports

    assert summarize_ports(listeners) == {
        "listeners": 3,
        "ports": 2,
        "processes": 1,
        "projects": 1,
        "unresolved": 1,
    }
    assert all(value == 0 for value in summarize_ports([]).values())


def test_summary_command(listeners):
    assert json.loads(invoke("summary", "--json"))["processes"] == 1
    assert "Listeners: 3" in invoke("summary")
    assert json.loads(invoke("summary", "--search", "missing", "--json"))["listeners"] == 0
    assert CliRunner().invoke(cli.app, ["summary", "--range", "2-1"]).exit_code == 2


def test_process_groups(listeners):
    report = json.loads(invoke("summary", "--group", "process", "--json"))
    assert report["groups"][0]["name"] == "Python"
    assert report["groups"][0]["listeners"] == 2
    assert "Unknown: 1 listeners" in invoke("summary", "--group", "process")


def test_project_groups_preserve_unknown_owners(listeners):
    report = json.loads(invoke("summary", "--group", "project", "--json"))
    assert [(item["name"], item["listeners"]) for item in report["groups"]] == [
        ("API", 2),
        ("Unknown", 1),
    ]
    assert "API: 2 listeners" in invoke("summary", "--group", "project")
