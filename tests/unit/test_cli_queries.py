import json
from unittest.mock import Mock

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


def test_list_csv_and_conflicting_formats(listeners):
    result = CliRunner().invoke(cli.app, ["list", "--csv", "--pid", "10"])
    assert result.exit_code == 0
    assert "3000,tcp,LISTENING,10,Python" in result.stdout
    assert CliRunner().invoke(cli.app, ["list", "--json", "--csv"]).exit_code == 2


def test_next_json(monkeypatch):
    monkeypatch.setattr(cli.service, "next_available", lambda port: port + 1)
    result = CliRunner().invoke(cli.app, ["next", "3000", "--json", "--verbose"])
    assert json.loads(result.stdout) == {"start": 3000, "port": 3001, "available": False}


def test_watch_count_stops_without_sleeping(listeners, monkeypatch):
    sleep = Mock()
    monkeypatch.setattr(cli.time, "sleep", sleep)
    result = CliRunner().invoke(cli.app, ["watch", "--count", "1"])
    assert result.exit_code == 0
    sleep.assert_not_called()


def test_version_skips_requested_subcommand(monkeypatch):
    scan = Mock(side_effect=AssertionError("must not scan"))
    monkeypatch.setattr(cli.service, "list_ports", scan)
    result = CliRunner().invoke(cli.app, ["--version", "list"])
    assert result.exit_code == 0
    assert "PortWatch" in result.stdout
    scan.assert_not_called()


@pytest.mark.parametrize("interval", ["nan", "inf"])
def test_watch_rejects_nonfinite_intervals(interval):
    result = CliRunner().invoke(cli.app, ["watch", "--interval", interval])
    assert result.exit_code == 2
