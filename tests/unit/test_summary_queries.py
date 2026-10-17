import json

import pytest
from typer.testing import CliRunner

import portwatch.cli as cli
from portwatch.domain.models import PortInfo


@pytest.fixture
def listeners(monkeypatch):
    items = [
        PortInfo(3000, "tcp", "LISTENING", pid=10, process_name="python", project_name="API"),
        PortInfo(3001, "tcp", "LISTENING", pid=10, process_name="python", project_name="API"),
        PortInfo(4000, "tcp", "LISTENING", pid=20, process_name="node", project_name="UI"),
    ]
    monkeypatch.setattr(cli.service, "list_ports", lambda bounds=None: items)
    return items


def invoke(*args):
    return CliRunner().invoke(cli.app, ["summary", *args])


def test_summary_disjoint_ports_and_exclusions(listeners):
    result = invoke("--ports", "3000-4000", "--exclude", "3001", "--json")
    assert result.exit_code == 0
    assert json.loads(result.stdout)["listeners"] == 2
    assert invoke("--ports", "0").exit_code == 2


def test_summary_pid_filter_counts_one_process_with_multiple_ports(listeners):
    result = invoke("--pid", "10", "--json")
    data = json.loads(result.stdout)
    assert data["listeners"] == 2 and data["processes"] == 1
    assert invoke("--pid", "0").exit_code == 2
