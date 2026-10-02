"""Unit and HTTP-level coverage for the local dashboard."""

from __future__ import annotations

import http.client
import json
import mimetypes
import sys
import threading
from collections.abc import Iterator
from pathlib import Path

import pytest

from portwatch.domain.exceptions import ProcessTerminationError
from portwatch.domain.models import PortInfo
from portwatch.web import assets
from portwatch.web.actions import StaleListenerError, terminate_listener
from portwatch.web.assets import read_static_asset, static_directory
from portwatch.web.request_data import MAX_REQUEST_BYTES, single_port_parameter
from portwatch.web.security import (
    CONTENT_SECURITY_POLICY,
    SECURITY_HEADERS,
    compare_session_token,
    expected_host,
    expected_origin,
    new_session_token,
)
from portwatch.web.server import DashboardHTTPServer, create_server


class FakePortService:
    def __init__(self, ports: list[PortInfo] | None = None) -> None:
        self.ports = ports or []
        self.error: OSError | None = None
        self.ranges: list[object] = []

    def list_ports(self, port_range: object = None) -> list[PortInfo]:
        self.ranges.append(port_range)
        if self.error:
            raise self.error
        return self.ports


class FakeTerminator:
    def __init__(self) -> None:
        self.pids: list[int] = []
        self.error: ProcessTerminationError | None = None

    def terminate(self, pid: int) -> None:
        self.pids.append(pid)
        if self.error:
            raise self.error


@pytest.fixture
def running_dashboard() -> Iterator[tuple[DashboardHTTPServer, FakePortService, FakeTerminator]]:
    service = FakePortService([PortInfo(3000, "tcp", "LISTENING", pid=42)])
    terminator = FakeTerminator()
    server = create_server(service, terminator)
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    try:
        yield server, service, terminator
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def request(
    server: DashboardHTTPServer,
    method: str,
    path: str,
    *,
    body: bytes | None = None,
    headers: dict[str, str] | None = None,
) -> tuple[int, dict[str, object] | bytes, http.client.HTTPMessage]:
    connection = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=2)
    connection.request(method, path, body=body, headers=headers or {})
    response = connection.getresponse()
    payload = response.read()
    result: dict[str, object] | bytes
    if response.getheader("Content-Type", "").startswith("application/json"):
        result = json.loads(payload)
    else:
        result = payload
    status = response.status
    response_headers = response.headers
    connection.close()
    return status, result, response_headers


def post_headers(server: DashboardHTTPServer, *, token: str | None = None) -> dict[str, str]:
    return {
        "Origin": server.url.rstrip("/"),
        "X-PortWatch-Token": token if token is not None else server.token,
    }


def test_request_data_accepts_defaults_and_single_decimal_value() -> None:
    assert single_port_parameter({}, "start", "1") == "1"
    assert single_port_parameter({"end": ["65535"]}, "end", "1") == "65535"


@pytest.mark.parametrize("values", [[], ["1", "2"], ["+1"], ["1.0"], [""]])
def test_request_data_rejects_ambiguous_or_non_decimal_values(values: list[str]) -> None:
    with pytest.raises(ValueError, match="Start must be a single port number"):
        single_port_parameter({"start": values}, "start", "1")


def test_security_token_and_header_policy() -> None:
    token = new_session_token()
    assert len(token) >= 40
    assert compare_session_token(token, token)
    assert not compare_session_token("wrong", token)
    assert SECURITY_HEADERS["Content-Security-Policy"] == CONTENT_SECURITY_POLICY
    assert SECURITY_HEADERS["Cache-Control"] == "no-store"


@pytest.mark.parametrize(
    ("host", "port", "accepted"),
    [
        ("127.0.0.1:8123", 8123, True),
        ("127.0.0.1", 80, True),
        ("localhost:8123", 8123, False),
        ("127.0.0.1:8124", 8123, False),
        ("user@127.0.0.1:8123", 8123, False),
        ("127.0.0.1:bad", 8123, False),
        ("127.0.0.1/path", 80, False),
        ("127.0.0.1?x=1", 80, False),
        ("127.0.0.1#fragment", 80, False),
    ],
)
def test_expected_host_accepts_only_exact_loopback_authority(
    host: str, port: int, accepted: bool
) -> None:
    assert expected_host(host, port) is accepted


@pytest.mark.parametrize(
    ("origin", "host", "port", "accepted"),
    [
        ("http://127.0.0.1:8123", "127.0.0.1:8123", 8123, True),
        ("http://127.0.0.1:8123/", "127.0.0.1:8123", 8123, True),
        ("https://127.0.0.1:8123", "127.0.0.1:8123", 8123, False),
        ("http://localhost:8123", "127.0.0.1:8123", 8123, False),
        ("http://127.0.0.1:8124", "127.0.0.1:8123", 8123, False),
        ("http://user@127.0.0.1:8123", "127.0.0.1:8123", 8123, False),
        ("http://127.0.0.1:8123/path", "127.0.0.1:8123", 8123, False),
        ("http://127.0.0.1:8123/?x=1", "127.0.0.1:8123", 8123, False),
        ("http://127.0.0.1:8123/#x", "127.0.0.1:8123", 8123, False),
        ("http://127.0.0.1:bad", "127.0.0.1:8123", 8123, False),
        ("http://127.0.0.1:8123", "evil.example", 8123, False),
    ],
)
def test_expected_origin_requires_same_loopback_origin(
    origin: str, host: str, port: int, accepted: bool
) -> None:
    assert expected_origin(origin, host, port) is accepted


def test_static_directory_resolves_source_and_frozen_bundle(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_directory = static_directory()
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", "C:/bundle", raising=False)
    assert static_directory() == Path("C:/bundle/portwatch/web/static")
    monkeypatch.setattr(sys, "frozen", False, raising=False)
    assert static_directory() == source_directory


def test_read_static_asset_handles_mime_and_default_index(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    (tmp_path / "index.html").write_text("dashboard", encoding="utf-8")
    (tmp_path / "style.css").write_text("body {}", encoding="utf-8")
    (tmp_path / "unknown.asset").write_bytes(b"data")
    monkeypatch.setattr(assets, "STATIC_DIRECTORY", tmp_path)

    assert read_static_asset("/") == ("text/html; charset=utf-8", b"dashboard")
    assert read_static_asset("/style.css")[0] == "text/css; charset=utf-8"
    monkeypatch.setattr(mimetypes, "guess_type", lambda _: ("application/javascript", None))
    assert read_static_asset("/unknown.asset")[0] == "application/javascript; charset=utf-8"
    monkeypatch.setattr(mimetypes, "guess_type", lambda _: ("application/json", None))
    assert read_static_asset("/unknown.asset")[0] == "application/json; charset=utf-8"
    monkeypatch.setattr(mimetypes, "guess_type", lambda _: (None, None))
    assert read_static_asset("/unknown.asset")[0] == "application/octet-stream"


@pytest.mark.parametrize(
    ("name", "mime"), [("app.js", "text/javascript"), ("app.css", "text/css")]
)
def test_packaged_assets_ignore_incorrect_windows_mime_registry(monkeypatch, tmp_path, name, mime):
    (tmp_path / name).write_text("content", encoding="utf-8")
    monkeypatch.setattr(assets, "STATIC_DIRECTORY", tmp_path)
    monkeypatch.setattr(mimetypes, "guess_type", lambda _: ("text/plain", None))
    assert read_static_asset(f"/{name}")[0] == f"{mime}; charset=utf-8"


def test_read_static_asset_rejects_missing_directory_and_escape(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    root = tmp_path / "static"
    root.mkdir()
    outside = tmp_path / "secret.txt"
    outside.write_text("secret", encoding="utf-8")
    monkeypatch.setattr(assets, "STATIC_DIRECTORY", root)

    with pytest.raises(OSError):
        read_static_asset("/missing.css")
    with pytest.raises(OSError):
        read_static_asset("/.")
    with pytest.raises(OSError):
        read_static_asset("/%2e%2e/secret.txt")


def test_terminate_listener_rechecks_identity_and_reports_stale_state() -> None:
    service = FakePortService([PortInfo(3000, "tcp", "LISTENING", pid=42)])
    terminator = FakeTerminator()
    assert terminate_listener(service, terminator, 3000, 42) == "Process 42 was asked to stop."
    assert terminator.pids == [42]

    service.ports = [PortInfo(3000, "tcp", "LISTENING", pid=99)]
    with pytest.raises(StaleListenerError, match="process using this port changed"):
        terminate_listener(service, terminator, 3000, 42)

    service.ports = []
    with pytest.raises(StaleListenerError, match="no longer listening"):
        terminate_listener(service, terminator, 3000, 42)


def test_server_binds_loopback_and_creates_unique_session() -> None:
    first = create_server(FakePortService(), FakeTerminator())
    second = create_server(FakePortService(), FakeTerminator())
    try:
        assert first.server_address[0] == "127.0.0.1"
        assert first.url == f"http://127.0.0.1:{first.server_port}/"
        assert first.token != second.token
    finally:
        first.server_close()
        second.server_close()


def test_get_routes_session_ports_and_static_assets(
    running_dashboard: tuple[DashboardHTTPServer, FakePortService, FakeTerminator],
) -> None:
    server, service, _ = running_dashboard
    status, session, headers = request(server, "GET", "/api/session")
    assert status == 200
    assert session == {"token": server.token}
    assert headers["Content-Security-Policy"] == CONTENT_SECURITY_POLICY
    assert headers["X-Frame-Options"] == "DENY"
    assert headers["Cache-Control"] == "no-store"

    status, ports, _ = request(server, "GET", "/api/ports?start=3000&end=3000")
    assert status == 200
    assert isinstance(ports, dict)
    assert ports["ports"][0]["port"] == 3000
    assert service.ranges[-1] is not None

    status, document, content_headers = request(server, "GET", "/")
    assert status == 200
    assert isinstance(document, bytes) and b"PortWatch" in document
    assert content_headers.get_content_type() == "text/html"

    status, script, script_headers = request(server, "GET", "/dashboard.js")
    assert status == 200
    assert isinstance(script, bytes) and script
    assert script_headers.get_content_type() in {"text/javascript", "application/javascript"}

    status, missing, _ = request(server, "GET", "/missing.asset")
    assert status == 404
    assert missing == {"error": "Dashboard asset not found."}


def test_get_rejects_foreign_host_invalid_ranges_and_system_errors(
    running_dashboard: tuple[DashboardHTTPServer, FakePortService, FakeTerminator],
) -> None:
    server, service, _ = running_dashboard
    status, payload, _ = request(server, "GET", "/api/session", headers={"Host": "example.com"})
    assert status == 403
    assert payload == {"error": "This dashboard is available on localhost only."}

    for query in ("start=2&start=3", "start=9000&end=3000", "start=0", "end=65536"):
        status, payload, _ = request(server, "GET", f"/api/ports?{query}")
        assert status == 400
        assert isinstance(payload, dict) and "error" in payload

    service.error = OSError("socket inventory unavailable")
    status, payload, _ = request(server, "GET", "/api/ports")
    assert status == 503
    assert payload == {"error": "socket inventory unavailable"}


def test_post_rejects_origin_token_and_unknown_action(
    running_dashboard: tuple[DashboardHTTPServer, FakePortService, FakeTerminator],
) -> None:
    server, _, _ = running_dashboard
    path = "/api/ports/3000/terminate"
    valid_headers = post_headers(server)

    for headers, message in (
        (
            {**valid_headers, "Origin": "https://127.0.0.1"},
            "Requests must come from this dashboard.",
        ),
        ({**valid_headers, "X-PortWatch-Token": "bad"}, "Refresh the dashboard and try again."),
    ):
        status, payload, _ = request(server, "POST", path, body=b"{}", headers=headers)
        assert status == 403
        assert payload == {"error": message}

    no_origin = {"X-PortWatch-Token": server.token}
    status, _, _ = request(server, "POST", path, body=b"{}", headers=no_origin)
    assert status == 403

    status, payload, _ = request(
        server,
        "POST",
        "/api/ports/3000/other",
        body=b"{}",
        headers=valid_headers,
    )
    assert status == 404
    assert payload == {"error": "This action is not available."}


@pytest.mark.parametrize(
    ("path", "body", "headers", "expected_status"),
    [
        ("/api/ports/3000/terminate", b"{}", {"Content-Type": "text/plain"}, 400),
        (
            "/api/ports/3000/terminate",
            b"{}",
            {"Content-Type": "application/json", "Content-Length": "abc"},
            400,
        ),
        (
            "/api/ports/3000/terminate",
            b"{}",
            {"Content-Type": "application/json", "Content-Length": str(MAX_REQUEST_BYTES + 1)},
            400,
        ),
        ("/api/ports/3000/terminate", b"{", {"Content-Type": "application/json"}, 400),
        ("/api/ports/3000/terminate", b"[]", {"Content-Type": "application/json"}, 400),
        ("/nope/3000/terminate", None, {"Content-Type": "application/json"}, 404),
        ("/api/ports/0/terminate", b"{}", {"Content-Type": "application/json"}, 400),
        ("/api/ports/65536/terminate", b"{}", {"Content-Type": "application/json"}, 400),
        ("/api/ports/abc/terminate", b"{}", {"Content-Type": "application/json"}, 400),
    ],
)
def test_post_rejects_invalid_payload_and_port(
    running_dashboard: tuple[DashboardHTTPServer, FakePortService, FakeTerminator],
    path: str,
    body: bytes | None,
    headers: dict[str, str],
    expected_status: int,
) -> None:
    server, _, _ = running_dashboard
    status, payload, _ = request(
        server,
        "POST",
        path,
        body=body,
        headers={**post_headers(server), **headers},
    )
    assert status == expected_status
    assert isinstance(payload, dict) and "error" in payload


@pytest.mark.parametrize("pid", [None, "42", True, 0, -1])
def test_post_rejects_invalid_pid(
    running_dashboard: tuple[DashboardHTTPServer, FakePortService, FakeTerminator], pid: object
) -> None:
    server, _, _ = running_dashboard
    body = json.dumps({"pid": pid}).encode()
    status, payload, _ = request(
        server,
        "POST",
        "/api/ports/3000/terminate",
        body=body,
        headers={**post_headers(server), "Content-Type": "application/json"},
    )
    assert status == 400
    assert payload == {"error": "A valid process ID is required."}


def test_post_terminates_only_the_confirmed_current_listener(
    running_dashboard: tuple[DashboardHTTPServer, FakePortService, FakeTerminator],
) -> None:
    server, _, terminator = running_dashboard
    status, payload, _ = request(
        server,
        "POST",
        "/api/ports/3000/terminate",
        body=b'{"pid":42}',
        headers={**post_headers(server), "Content-Type": "application/json"},
    )
    assert status == 200
    assert payload == {"message": "Process 42 was asked to stop."}
    assert terminator.pids == [42]


def test_post_maps_stale_termination_and_os_errors_to_http_status(
    running_dashboard: tuple[DashboardHTTPServer, FakePortService, FakeTerminator],
) -> None:
    server, service, terminator = running_dashboard
    headers = {**post_headers(server), "Content-Type": "application/json"}

    service.ports = []
    status, payload, _ = request(
        server, "POST", "/api/ports/3000/terminate", body=b'{"pid":42}', headers=headers
    )
    assert status == 409
    assert payload == {"error": "Port 3000 is no longer listening. Rescan before trying again."}

    service.error = OSError("inventory failed")
    status, payload, _ = request(
        server, "POST", "/api/ports/3000/terminate", body=b'{"pid":42}', headers=headers
    )
    assert status == 503
    assert payload == {"error": "inventory failed"}

    service.error = None
    service.ports = [PortInfo(3000, "tcp", "LISTENING", pid=42)]
    terminator.error = ProcessTerminationError("permission denied")
    status, payload, _ = request(
        server, "POST", "/api/ports/3000/terminate", body=b'{"pid":42}', headers=headers
    )
    assert status == 409
    assert payload == {"error": "permission denied"}
