from collections.abc import Iterable
from typing import Protocol

import psutil

from portwatch.domain.models import PortInfo


class NetworkScanner(Protocol):
    def list_listening_ports(self) -> list[PortInfo]: ...


class PsutilNetworkScanner:
    def list_listening_ports(self) -> list[PortInfo]:
        ports: dict[tuple[int, str, int | None], PortInfo] = {}
        for connection in self._connections():
            if connection.status != psutil.CONN_LISTEN or not connection.laddr:
                continue
            port = int(connection.laddr.port)
            protocol = "tcp" if connection.type == psutil.SOCK_STREAM else "udp"
            key = (port, protocol, connection.pid)
            ports[key] = PortInfo(
                port=port,
                protocol=protocol,
                status="LISTENING",
                pid=connection.pid,
            )
        return sorted(ports.values(), key=lambda item: (item.port, item.protocol, item.pid or 0))

    @staticmethod
    def _connections() -> Iterable[psutil._common.sconn]:
        try:
            return psutil.net_connections(kind="inet")
        except psutil.AccessDenied:
            return []
