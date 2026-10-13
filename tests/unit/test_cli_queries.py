import json

import pytest
from typer.testing import CliRunner

import portwatch.cli as cli
from portwatch.domain.models import PortInfo


@pytest.fixture
def listeners(monkeypatch):
    ports = [
        PortInfo(3000, "tcp", "LISTENING", pid=10, process_name="Python", project_name="Backend"),
        PortInfo(4000, "tcp", "LISTENING", pid=20, process_name="node", project_name="Frontend"),
    ]
    monkeypatch.setattr(cli.service, "list_ports", lambda port_range=None: ports)
    return ports


def test_list_search(listeners):
    result = CliRunner().invoke(cli.app, ["list", "--search", "BACKEND", "--json"])
    assert result.exit_code == 0
    assert [item["port"] for item in json.loads(result.stdout)] == [3000]


def test_list_pid_filter(listeners):
    result = CliRunner().invoke(cli.app, ["list", "--pid", "20", "--json"])
    assert [item["port"] for item in json.loads(result.stdout)] == [4000]
    assert CliRunner().invoke(cli.app, ["list", "--pid", "0"]).exit_code == 2


def test_list_process_filter(listeners):
    result = CliRunner().invoke(cli.app, ["list", "--process", "py", "--json"])
    assert [item["pid"] for item in json.loads(result.stdout)] == [10]


def test_list_project_filters_combine(listeners):
    result = CliRunner().invoke(cli.app, ["list", "--project", "front", "--pid", "10", "--json"])
    assert json.loads(result.stdout) == []


def test_list_sort_by_process(listeners):
    result = CliRunner().invoke(cli.app, ["list", "--sort", "process", "--json"])
    assert [item["port"] for item in json.loads(result.stdout)] == [4000, 3000]
    assert CliRunner().invoke(cli.app, ["list", "--sort", "bad"]).exit_code == 2


def test_list_descending_sort(listeners):
    result = CliRunner().invoke(cli.app, ["list", "--descending", "--json"])
    assert [item["port"] for item in json.loads(result.stdout)] == [4000, 3000]
