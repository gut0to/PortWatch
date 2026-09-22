from types import SimpleNamespace

import psutil

from portwatch.system.network import PsutilNetworkScanner


def test_network_scanner_filters_and_deduplicates(monkeypatch) -> None:
    entries = [
        SimpleNamespace(
            status=psutil.CONN_LISTEN, laddr=("127.0.0.1", 3000), type=psutil.SOCK_STREAM, pid=5
        ),
        SimpleNamespace(
            status=psutil.CONN_LISTEN, laddr=("::", 3000), type=psutil.SOCK_STREAM, pid=5
        ),
        SimpleNamespace(
            status="ESTABLISHED", laddr=("127.0.0.1", 4000), type=psutil.SOCK_STREAM, pid=6
        ),
    ]
    monkeypatch.setattr(PsutilNetworkScanner, "_connections", staticmethod(lambda: entries))

    result = PsutilNetworkScanner().list_listening_ports()

    assert [(item.port, item.pid) for item in result] == [(3000, 5)]
