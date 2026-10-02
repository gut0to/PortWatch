"""Serve the local dashboard and its loopback-only API."""

from __future__ import annotations

import json
from datetime import datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import cast
from urllib.parse import parse_qs, urlsplit

from portwatch.domain.exceptions import (
    InvalidPortError,
    ProcessTerminationError,
)
from portwatch.presentation.serializers import port_to_dict
from portwatch.services.port_service import PortService
from portwatch.system.termination import ProcessTerminator
from portwatch.utils.ports import parse_port_range
from portwatch.web.actions import StaleListenerError, terminate_listener
from portwatch.web.assets import read_static_asset
from portwatch.web.security import (
    LOOPBACK_HOST,
    SECURITY_HEADERS,
    compare_session_token,
    expected_host,
    expected_origin,
    new_session_token,
)

MAX_REQUEST_BYTES = 4096
MAX_PORT = 65535


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


class DashboardRequestHandler(BaseHTTPRequestHandler):
    """Route static files and small JSON operations without opening CORS."""

    server: DashboardHTTPServer
    server_version = "PortWatch"
    sys_version = ""

    def do_GET(self) -> None:
        if not self._has_expected_host():
            self._send_error(HTTPStatus.FORBIDDEN, "This dashboard is available on localhost only.")
            return

        request = urlsplit(self.path)
        if request.path == "/api/session":
            self._send_json(HTTPStatus.OK, {"token": self.server.token})
            return
        if request.path == "/api/ports":
            self._list_ports(request.query)
            return
        self._serve_static(request.path)

    def do_POST(self) -> None:
        request = urlsplit(self.path)
        if not self._has_expected_origin():
            self._send_error(HTTPStatus.FORBIDDEN, "Requests must come from this dashboard.")
            return
        if not compare_session_token(
            self.headers.get("X-PortWatch-Token", ""), self.server.token
        ):
            self._send_error(HTTPStatus.FORBIDDEN, "Refresh the dashboard and try again.")
            return

        parts = request.path.strip("/").split("/")
        if len(parts) != 4 or parts[:2] != ["api", "ports"] or parts[3] != "terminate":
            self._send_error(HTTPStatus.NOT_FOUND, "This action is not available.")
            return
        self._terminate_port(parts[2])

    def log_message(self, format_string: str, *args: object) -> None:
        """Keep routine local requests out of the CLI output."""

    def _list_ports(self, query: str) -> None:
        parameters = parse_qs(query, strict_parsing=False)
        try:
            start = self._single_parameter(parameters, "start", "1")
            end = self._single_parameter(parameters, "end", str(MAX_PORT))
            port_range = parse_port_range(f"{start}-{end}")
            ports = self.server.service.list_ports(port_range)
        except (InvalidPortError, ValueError) as error:
            self._send_error(HTTPStatus.BAD_REQUEST, str(error))
            return
        except OSError as error:
            self._send_error(HTTPStatus.SERVICE_UNAVAILABLE, str(error))
            return

        self._send_json(
            HTTPStatus.OK,
            {
                "ports": [port_to_dict(port) for port in ports],
                "scanned_at": self._now_iso(),
            },
        )

    def _terminate_port(self, raw_port: str) -> None:
        try:
            port = int(raw_port)
            if not 1 <= port <= MAX_PORT:
                raise ValueError("Port must be between 1 and 65535.")
            payload = self._read_json_body()
            pid = payload.get("pid")
            if not isinstance(pid, int) or isinstance(pid, bool) or pid <= 0:
                raise ValueError("A valid process ID is required.")
        except (ValueError, json.JSONDecodeError) as error:
            self._send_error(HTTPStatus.BAD_REQUEST, str(error))
            return

        try:
            message = terminate_listener(self.server.service, self.server.terminator, port, pid)
        except StaleListenerError as error:
            self._send_error(HTTPStatus.CONFLICT, str(error))
            return
        except OSError as error:
            self._send_error(HTTPStatus.SERVICE_UNAVAILABLE, str(error))
            return
        except ProcessTerminationError as error:
            self._send_error(HTTPStatus.CONFLICT, str(error))
            return

        self._send_json(HTTPStatus.OK, {"message": message})

    def _read_json_body(self) -> dict[str, object]:
        if self.headers.get_content_type() != "application/json":
            raise ValueError("The request must use JSON.")
        raw_length = self.headers.get("Content-Length", "")
        if not raw_length.isdecimal():
            raise ValueError("A JSON request body is required.")
        length = int(raw_length)
        if length > MAX_REQUEST_BYTES:
            raise ValueError("The request is too large.")
        data = json.loads(self.rfile.read(length))
        if not isinstance(data, dict):
            raise ValueError("The request body must be a JSON object.")
        return cast(dict[str, object], data)

    def _serve_static(self, request_path: str) -> None:
        try:
            content_type, body = read_static_asset(request_path)
        except OSError:
            self._send_error(HTTPStatus.NOT_FOUND, "Dashboard asset not found.")
            return

        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self._security_headers()
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, status: HTTPStatus, data: object) -> None:
        body = json.dumps(data, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self._security_headers()
        self.end_headers()
        self.wfile.write(body)

    def _send_error(self, status: HTTPStatus, message: str) -> None:
        self._send_json(status, {"error": message})

    def _security_headers(self) -> None:
        for name, value in SECURITY_HEADERS.items():
            self.send_header(name, value)

    def _has_expected_host(self) -> bool:
        return expected_host(self.headers.get("Host", ""), self.server.server_port)

    def _has_expected_origin(self) -> bool:
        return expected_origin(
            self.headers.get("Origin", ""),
            self.headers.get("Host", ""),
            self.server.server_port,
        )

    @staticmethod
    def _single_parameter(parameters: dict[str, list[str]], key: str, default: str) -> str:
        values = parameters.get(key, [default])
        if len(values) != 1 or not values[0].isdecimal():
            raise ValueError(f"{key.title()} must be a single port number.")
        return values[0]

    @staticmethod
    def _now_iso() -> str:
        return datetime.now().astimezone().isoformat(timespec="seconds")


def create_server(
    service: PortService,
    terminator: ProcessTerminator,
    port: int = 0,
) -> DashboardHTTPServer:
    """Create a server on IPv4 loopback, using a fresh token for write requests."""
    return DashboardHTTPServer(port, service, terminator, new_session_token())
