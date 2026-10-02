"""Serve the local dashboard and its loopback-only API."""

from __future__ import annotations

from http.server import ThreadingHTTPServer

from portwatch.services.port_service import PortService
from portwatch.system.termination import ProcessTerminator
from portwatch.web.handler import DashboardRequestHandler
from portwatch.web.security import LOOPBACK_HOST, new_session_token


class DashboardHTTPServer(ThreadingHTTPServer):
    """Carry the app services and per-run token into request handlers."""

    daemon_threads = True
    allow_reuse_address = True

    def __init__(
        self,
        port: int,
        service: PortService,
        terminator: ProcessTerminator,
        token: str,
    ) -> None:
        self.service = service
        self.terminator = terminator
        self.token = token
        super().__init__((LOOPBACK_HOST, port), DashboardRequestHandler)

    @property
    def url(self) -> str:
        return f"http://{LOOPBACK_HOST}:{self.server_port}/"


def create_server(
    service: PortService,
    terminator: ProcessTerminator,
    port: int = 0,
) -> DashboardHTTPServer:
    """Create a server on IPv4 loopback, using a fresh token for write requests."""
    return DashboardHTTPServer(port, service, terminator, new_session_token())
