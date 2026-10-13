import pytest

from portwatch.web.request_data import single_port_parameter


@pytest.mark.parametrize("value", ["١", "1" * 5000, "000001"])
def test_port_parameter_rejects_unbounded_and_unicode_numbers(value):
    with pytest.raises(ValueError):
        single_port_parameter({"start": [value]}, "start", "1")


def test_action_json_rejects_duplicate_pid():
    import json

    from portwatch.web.request_data import unique_json_object

    with pytest.raises(ValueError, match="Duplicate JSON field"):
        json.loads('{"pid":42,"pid":99}', object_pairs_hook=unique_json_object)
    assert unique_json_object([("pid", 42)]) == {"pid": 42}


def test_empty_json_body_has_actionable_error():
    from email.message import Message
    from io import BytesIO

    from portwatch.web.handler import DashboardRequestHandler

    handler = object.__new__(DashboardRequestHandler)
    handler.headers = Message()
    handler.headers["Content-Type"] = "application/json"
    handler.headers["Content-Length"] = "0"
    handler.rfile = BytesIO()
    with pytest.raises(ValueError, match="JSON request body is required"):
        handler._read_json_body()


def test_oversized_query_returns_bad_request_without_scanning():
    from unittest.mock import Mock

    from portwatch.web.handler import DashboardRequestHandler

    handler = object.__new__(DashboardRequestHandler)
    handler._send_error = Mock()
    handler._list_ports("&".join("start=1" for _ in range(17)))
    assert handler._send_error.call_args.args[0] == 400


def test_request_setup_limits_idle_socket_reads(monkeypatch):
    from http.server import BaseHTTPRequestHandler
    from unittest.mock import Mock

    from portwatch.web.handler import DashboardRequestHandler

    handler = object.__new__(DashboardRequestHandler)
    handler.request = Mock()
    monkeypatch.setattr(BaseHTTPRequestHandler, "setup", lambda self: None)
    handler.setup()
    handler.request.settimeout.assert_called_once_with(10)


def test_termination_rejects_reused_pid_and_requires_start_time():
    from datetime import datetime
    from unittest.mock import Mock

    from portwatch.domain.models import PortInfo
    from portwatch.web.actions import StaleListenerError, terminate_listener

    service = Mock()
    item = PortInfo(3000, "tcp", "LISTENING", pid=42, started_at=datetime(2026, 1, 1))
    service.list_ports.return_value = [item]
    terminator = Mock()
    for timestamp in (None, "2025-01-01T00:00:00"):
        with pytest.raises(StaleListenerError):
            terminate_listener(service, terminator, 3000, 42, timestamp)
    terminator.terminate.assert_not_called()
    terminate_listener(service, terminator, 3000, 42, item.started_at.isoformat())
    terminator.terminate.assert_called_once_with(42)
