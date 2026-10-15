import http.client
from email.message import Message
from io import BytesIO

import pytest
from tests.unit.test_web import running_dashboard as running_dashboard

from portwatch.web.handler import DashboardRequestHandler


@pytest.mark.parametrize("path", ["/", "/api/session", "/api/ports", "/missing.css"])
def test_head_returns_get_headers_without_a_body(running_dashboard, path):
    server, _, _ = running_dashboard
    connection = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=2)
    connection.request("GET", path)
    response = connection.getresponse()
    status = response.status
    body = response.read()
    connection.close()
    connection = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=2)
    connection.request("HEAD", path)
    response = connection.getresponse()
    assert response.status == status
    assert response.read() == b""
    assert int(response.getheader("Content-Length")) == len(body)
    assert response.getheader("X-Frame-Options") == "DENY"
    connection.close()


def body_handler(headers, body=b"{}"):
    handler = object.__new__(DashboardRequestHandler)
    handler.headers = Message()
    handler.headers["Content-Type"] = "application/json"
    for name, value in headers:
        handler.headers[name] = value
    handler.rfile = BytesIO(body)
    return handler


@pytest.mark.parametrize(
    "headers",
    [
        [],
        [("Content-Length", "2"), ("Content-Length", "2")],
        [("Content-Length", "2"), ("Transfer-Encoding", "chunked")],
        [("Content-Length", "٢")],
        [("Content-Length", "2" * 5000)],
        [("Content-Length", "2,2")],
        [("Content-Length", "+2")],
    ],
)
def test_action_framing_is_unambiguous_and_bounded(headers):
    with pytest.raises(ValueError):
        body_handler(headers)._read_json_body()


def test_action_framing_accepts_a_single_bounded_length():
    assert body_handler([("Content-Length", "2")])._read_json_body() == {}


@pytest.mark.parametrize("constant", ["NaN", "Infinity", "-Infinity", "1e9999", "-1e9999"])
def test_action_json_rejects_nonfinite_numbers_even_in_unused_fields(constant):
    body = ('{"pid":42,"extra":' + constant + "}").encode()
    with pytest.raises(ValueError, match="Non-finite JSON"):
        body_handler([("Content-Length", str(len(body)))], body)._read_json_body()


def test_action_json_accepts_finite_numeric_metadata():
    body = b'{"pid":42,"extra":1.25}'
    payload = body_handler([("Content-Length", str(len(body)))], body)._read_json_body()
    assert payload == {"pid": 42, "extra": 1.25}
