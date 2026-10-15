import json

import pytest
from typer.testing import CliRunner

import portwatch.cli as cli
from portwatch.domain.exceptions import InvalidPortError
from portwatch.domain.models import PortInfo, PortRange


@pytest.mark.parametrize(
    "start,end", [(0, 1), (3, 2), (1, 65536), (True, 2), (1, False), (1.5, 2), (1, "2")]
)
def test_range_invariant(start, end):
    with pytest.raises(InvalidPortError):
        PortRange(start, end)


@pytest.fixture
def listeners(monkeypatch):
    items = [
        PortInfo(3000, "tcp", "LISTENING", pid=10, process_name="Python", project_name="API"),
        PortInfo(
            4000, "tcp", "LISTENING", pid=20, process_name="python-worker", project_name="api-tools"
        ),
        PortInfo(4000, "tcp", "LISTENING", pid=30, process_name="node"),
    ]
    monkeypatch.setattr(cli.service, "list_ports", lambda port_range=None: items)
    return items


def invoke(*args):
    result = CliRunner().invoke(cli.app, list(args))
    assert result.exit_code == 0, result.output
    return result.stdout


def test_port_selection_union():
    from portwatch.utils.ports import parse_port_selection

    assert parse_port_selection("3000, 3001-3003,3000") == frozenset(range(3000, 3004))
    for value in ("", "1,", "0", "2-1", "x", "1" * 4097):
        with pytest.raises(InvalidPortError):
            parse_port_selection(value)


def test_list_selection(listeners):
    assert [
        item["pid"] for item in json.loads(invoke("list", "--ports", "4000,5000-5001", "--json"))
    ] == [20, 30]
    assert CliRunner().invoke(cli.app, ["list", "--ports", "0"]).exit_code == 2


def test_exclude_combines_with_selection(listeners):
    result = json.loads(invoke("list", "--ports", "3000-5000", "--exclude", "4000", "--json"))
    assert [item["port"] for item in result] == [3000]
    assert CliRunner().invoke(cli.app, ["list", "--exclude", "0"]).exit_code == 2


def test_search_terms_can_match_different_fields(listeners):
    result = json.loads(invoke("list", "--search", "python 3000", "--json"))
    assert [item["pid"] for item in result] == [10]
    assert json.loads(invoke("list", "--search", "python missing", "--json")) == []


def test_search_can_exclude_metadata_terms(listeners):
    result = json.loads(invoke("list", "--search", "python -worker", "--json"))
    assert [item["pid"] for item in result] == [10]
    assert len(json.loads(invoke("list", "--search=-missing", "--json"))) == 3


def test_exact_filters_distinguish_related_processes(listeners):
    from portwatch.services.port_filters import filter_ports

    assert [item.pid for item in filter_ports(listeners, process="PYTHON", exact=True)] == [10]
    assert [item.pid for item in filter_ports(listeners, project="api", exact=True)] == [10]
    assert len(filter_ports(listeners, process="python")) == 2


def test_cli_exact_filter(listeners):
    result = json.loads(
        invoke("list", "--process", "python", "--project", "API", "--exact", "--json")
    )
    assert [item["pid"] for item in result] == [10]
