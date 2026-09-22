import socket
from types import SimpleNamespace
from unittest.mock import Mock

import psutil

from portwatch.system.network import PsutilNetworkScanner


def test_network_scanner_filters_and_deduplicates(monkeypatch) -> None:
    entries = [
        SimpleNamespace(
            status=psutil.CONN_LISTEN,
            laddr=("127.0.0.1", 3000),
            type=socket.SOCK_STREAM,
            pid=5,
        ),
        SimpleNamespace(
            status=psutil.CONN_LISTEN,
            laddr=("::", 3000),
            type=socket.SOCK_STREAM,
            pid=5,
        ),
        SimpleNamespace(
            status="ESTABLISHED",
            laddr=("127.0.0.1", 4000),
            type=socket.SOCK_STREAM,
            pid=6,
        ),
    ]
    monkeypatch.setattr(PsutilNetworkScanner, "_connections", staticmethod(lambda: entries))

    result = PsutilNetworkScanner().list_listening_ports()

    assert [(item.port, item.pid) for item in result] == [(3000, 5)]


def test_network_scanner_handles_unusable_address_and_access_denied(monkeypatch) -> None:
    entries = [
        SimpleNamespace(status=psutil.CONN_LISTEN, laddr=("bad",), type=socket.SOCK_STREAM, pid=1)
    ]
    monkeypatch.setattr(PsutilNetworkScanner, "_connections", staticmethod(lambda: entries))
    assert PsutilNetworkScanner().list_listening_ports() == []

    monkeypatch.undo()
    monkeypatch.setattr(
        "portwatch.system.network.psutil.net_connections", Mock(side_effect=psutil.AccessDenied())
    )
    assert list(PsutilNetworkScanner._connections()) == []


def test_network_scanner_reads_object_port() -> None:
    address = SimpleNamespace(port=4321)

    assert PsutilNetworkScanner._port_from_address(address) == 4321
    assert PsutilNetworkScanner._port_from_address("invalid") is None
