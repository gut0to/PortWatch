from __future__ import annotations

import socket
from collections.abc import Iterable
from typing import Protocol, cast

import psutil

from portwatch.domain.exceptions import PermissionDeniedError
from portwatch.domain.models import PortInfo


class ConnectionRecord(Protocol):
    status: str
    laddr: object
    type: int
    pid: int | None


class NetworkScanner(Protocol):
    def list_listening_ports(self) -> list[PortInfo]: ...


class PsutilNetworkScanner:
    def list_listening_ports(self) -> list[PortInfo]:
        ports: dict[tuple[int, str, int | None], PortInfo] = {}
        for connection in self._connections():
            if connection.status != psutil.CONN_LISTEN or not connection.laddr:
                continue
            port = self._port_from_address(connection.laddr)
            if port is None:
                continue
            protocol = "tcp" if connection.type == socket.SOCK_STREAM else "udp"
            key = (port, protocol, connection.pid)
            ports[key] = PortInfo(
                port=port,
                protocol=protocol,
                status="LISTENING",
                pid=connection.pid,
            )
        return sorted(ports.values(), key=lambda item: (item.port, item.protocol, item.pid or 0))

    @staticmethod
    def _connections() -> Iterable[ConnectionRecord]:
        try:
            return cast(Iterable[ConnectionRecord], psutil.net_connections(kind="inet"))
        except psutil.AccessDenied as error:
            raise PermissionDeniedError(
                "Insufficient permission to scan TCP listeners. Try an elevated terminal."
            ) from error

    @staticmethod
    def _port_from_address(address: object) -> int | None:
        port = getattr(address, "port", None)
        if port is not None:
            return int(port)
        if isinstance(address, tuple) and len(address) >= 2:
            return int(address[1])
        return None
