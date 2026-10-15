import json
from datetime import UTC
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from typer.testing import CliRunner

import portwatch.cli as cli
import portwatch.system.processes as processes
from portwatch.domain.models import PortInfo
from portwatch.system.processes import PsutilProcessResolver


@pytest.mark.parametrize("platform", ["nt", "posix"])
def test_command_display_quotes_argument_boundaries(monkeypatch, platform):
    import shlex
    import subprocess

    monkeypatch.setattr(processes, "os", SimpleNamespace(name=platform))
    process = Mock()
    process.cmdline.return_value = ["python", "folder with spaces/server.py", "--token=a b"]
    expected = (
        subprocess.list2cmdline(process.cmdline.return_value)
        if platform == "nt"
        else shlex.join(process.cmdline.return_value)
    )
    assert PsutilProcessResolver._safe_cmdline(process) == expected
    process.cmdline.return_value = []
    assert PsutilProcessResolver._safe_cmdline(process) is None


@pytest.mark.parametrize("timestamp", [float("nan"), float("inf"), float("-inf"), 1e50])
def test_invalid_process_timestamps_do_not_abort_scan(timestamp):
    process = Mock()
    process.create_time.return_value = timestamp
    assert PsutilProcessResolver._safe_create_time(process) is None


def test_elapsed_time_accepts_timezone_aware_snapshots():
    from datetime import datetime, timedelta

    from portwatch.presentation.console import format_started

    assert "2m" in format_started(datetime.now(UTC) - timedelta(minutes=2, seconds=3))
    assert format_started(datetime.now(UTC) + timedelta(days=1)) == "0s ago"


def test_non_stream_records_are_never_exposed_as_tcp_listeners(monkeypatch):
    import socket

    import psutil

    from portwatch.system.network import PsutilNetworkScanner

    entry = SimpleNamespace(
        status=psutil.CONN_LISTEN, laddr=("localhost", 3000), type=socket.SOCK_DGRAM, pid=42
    )
    monkeypatch.setattr(PsutilNetworkScanner, "_connections", staticmethod(lambda: [entry]))
    assert PsutilNetworkScanner().list_listening_ports() == []


@pytest.mark.parametrize("pid", [0, -1, True, None, "42"])
def test_unusable_socket_owners_remain_unresolved(monkeypatch, pid):
    import socket

    import psutil

    from portwatch.system.network import PsutilNetworkScanner

    entry = SimpleNamespace(
        status=psutil.CONN_LISTEN, laddr=("localhost", 3000), type=socket.SOCK_STREAM, pid=pid
    )
    monkeypatch.setattr(PsutilNetworkScanner, "_connections", staticmethod(lambda: [entry]))
    assert PsutilNetworkScanner().list_listening_ports()[0].pid is None


def test_available_port_search_obeys_end(monkeypatch):
    from portwatch.domain.exceptions import InvalidPortError, PortNotFoundError
    from portwatch.services.port_service import PortService

    scanner = Mock()
    scanner.list_listening_ports.return_value = [PortInfo(3000, "tcp", "LISTENING")]
    service = PortService(scanner=scanner)
    assert service.next_available(3000, 3001) == 3001
    with pytest.raises(PortNotFoundError):
        service.next_available(3000, 3000)
    with pytest.raises(InvalidPortError):
        service.next_available(3001, 3000)
    monkeypatch.setattr(cli, "service", service)
    result = CliRunner().invoke(cli.app, ["next", "3000", "--end", "3001"])
    assert result.exit_code == 0 and result.stdout.strip() == "3001"


def test_multiple_available_ports_use_one_scan(monkeypatch):
    from portwatch.domain.exceptions import InvalidPortError, PortNotFoundError
    from portwatch.services.port_service import PortService

    scanner = Mock()
    scanner.list_listening_ports.return_value = [PortInfo(3001, "tcp", "LISTENING")]
    service = PortService(scanner=scanner)
    assert service.available_ports(3000, 2, 3003) == [3000, 3002]
    scanner.list_listening_ports.assert_called_once()
    for count in (0, True, 1.5):
        with pytest.raises(InvalidPortError):
            service.available_ports(3000, count)
    with pytest.raises(PortNotFoundError):
        service.available_ports(65535, 2)
    monkeypatch.setattr(cli, "service", service)
    runner = CliRunner()
    result = runner.invoke(cli.app, ["next", "3000", "--count", "2", "--json"])
    assert json.loads(result.stdout)["ports"] == [3000, 3002]
    assert runner.invoke(cli.app, ["next", "3000", "--count", "2"]).stdout == "3000\n3002\n"
    assert (
        "Available port: 3000"
        in runner.invoke(cli.app, ["next", "3000", "--count", "2", "--verbose"]).stdout
    )
    assert runner.invoke(cli.app, ["next", "65535", "--count", "2"]).exit_code == 3
    assert runner.invoke(cli.app, ["next", "4000", "--end", "3000", "--count", "2"]).exit_code == 2


def test_json_watch_is_bounded_and_machine_readable(monkeypatch):
    monkeypatch.setattr(
        cli.service, "list_ports", lambda bounds=None: [PortInfo(3000, "tcp", "LISTENING")]
    )
    sleep = Mock()
    monkeypatch.setattr(cli.time, "sleep", sleep)
    result = CliRunner().invoke(cli.app, ["watch", "--count", "2", "--json"])
    assert result.exit_code == 0
    rows = [json.loads(line) for line in result.stdout.splitlines()]
    assert len(rows) == 2
    assert rows[0]["ports"][0]["port"] == 3000
    sleep.assert_called_once_with(2.0)


def test_watch_changes_ignore_order_and_count_attempts(monkeypatch):
    from portwatch.services.monitoring import watch_snapshots

    first = PortInfo(1, "tcp", "LISTENING")
    second = PortInfo(2, "tcp", "LISTENING")
    scans = Mock(side_effect=[[first, second], [second, first], [], []])
    sleep = Mock()
    assert list(watch_snapshots(scans, 0.2, 4, changes_only=True, sleep=sleep)) == [
        [first, second],
        [],
    ]
    assert sleep.call_count == 3
    monkeypatch.setattr(cli.service, "list_ports", lambda bounds=None: [])
    monkeypatch.setattr(cli.time, "sleep", Mock())
    result = CliRunner().invoke(cli.app, ["watch", "--count", "3", "--changes-only", "--json"])
    assert len(result.stdout.splitlines()) == 1
