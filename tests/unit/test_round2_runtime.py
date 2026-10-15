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
