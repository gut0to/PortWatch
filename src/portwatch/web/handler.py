"""HTTP routes for the local dashboard."""

from __future__ import annotations

import json
import time
from datetime import datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler
from typing import TYPE_CHECKING, cast
from urllib.parse import parse_qs, urlsplit

from portwatch.domain.exceptions import InvalidPortError, ProcessTerminationError
from portwatch.presentation.serializers import port_to_dict
from portwatch.utils.ports import parse_port_range
from portwatch.web.actions import StaleListenerError, terminate_listener
from portwatch.web.assets import read_static_asset
from portwatch.web.request_data import (
    MAX_PORT,
    MAX_REQUEST_BYTES,
    finite_json_float,
    reject_json_constant,
    single_port_parameter,
    unique_json_object,
)
from portwatch.web.security import (
    SECURITY_HEADERS,
    compare_session_token,
    expected_host,
    expected_origin,
)

if TYPE_CHECKING:
    from portwatch.web.server import DashboardHTTPServer


class DashboardRequestHandler(BaseHTTPRequestHandler):
    """Route static files and small JSON operations without opening CORS."""

    server: DashboardHTTPServer
    server_version = "PortWatch"
    sys_version = ""

    def setup(self) -> None:
        self.request.settimeout(10)
        super().setup()

    def do_HEAD(self) -> None:
        self.do_GET()

    def do_GET(self) -> None:
        if not self._has_expected_host():
            self._send_error(HTTPStatus.FORBIDDEN, "This dashboard is available on localhost only.")
            return

        request = urlsplit(self.path)
        if request.path == "/api/health":
            from portwatch import __version__

            self._send_json(
                HTTPStatus.OK,
                {
                    "status": "ready",
                    "version": __version__,
                    "uptime_seconds": max(0.0, time.monotonic() - self.server.started_at),
                },
            )
            return
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
        if not compare_session_token(self.headers.get("X-PortWatch-Token", ""), self.server.token):
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
        try:
            parameters = parse_qs(
                query, strict_parsing=False, keep_blank_values=True, max_num_fields=16
            )
            start = single_port_parameter(parameters, "start", "1")
            end = single_port_parameter(parameters, "end", str(MAX_PORT))
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
            started_at = payload.get("started_at")
            if started_at is not None and not isinstance(started_at, str):
                raise ValueError("Process start time must be a string or null.")
            pid = payload.get("pid")
            if not isinstance(pid, int) or isinstance(pid, bool) or pid <= 0:
                raise ValueError("A valid process ID is required.")
        except (ValueError, UnicodeDecodeError, TimeoutError) as error:
            self._send_error(HTTPStatus.BAD_REQUEST, str(error))
            return

        try:
            message = terminate_listener(
                self.server.service, self.server.terminator, port, pid, started_at
            )
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
        if self.headers.get("Transfer-Encoding") is not None:
            raise ValueError("Transfer-encoded action bodies are not supported.")
        lengths = self.headers.get_all("Content-Length", [])
        if len(lengths) != 1:
            raise ValueError("Exactly one Content-Length header is required.")
        raw_length = lengths[0]
        if not 1 <= len(raw_length) <= 4 or not raw_length.isascii() or not raw_length.isdecimal():
            raise ValueError("A JSON request body is required.")
        length = int(raw_length)
        if length == 0:
            raise ValueError("A JSON request body is required.")
        if length > MAX_REQUEST_BYTES:
            raise ValueError("The request is too large.")
        data = json.loads(
            self.rfile.read(length),
            object_pairs_hook=unique_json_object,
            parse_constant=reject_json_constant,
            parse_float=finite_json_float,
        )
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
        if self.command != "HEAD":
            self.wfile.write(body)

    def _send_json(self, status: HTTPStatus, data: object) -> None:
        body = json.dumps(data, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self._security_headers()
        self.end_headers()
        if self.command != "HEAD":
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
    def _now_iso() -> str:
        return datetime.now().astimezone().isoformat(timespec="seconds")
