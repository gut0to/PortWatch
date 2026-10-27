import pytest
from tests.unit.test_web import request
from tests.unit.test_web import running_dashboard as running_dashboard


def test_health_route_reports_server_readiness_without_scanning(running_dashboard):
    server, service, _ = running_dashboard
    status, result, headers = request(server, "GET", "/api/health")
    assert status == 200 and result["status"] == "ready"
    assert result["uptime_seconds"] >= 0 and result["version"]
    assert headers["Cache-Control"] == "no-store"
    assert service.ranges == []


def test_unknown_scan_query_parameters_are_rejected_without_scanning(running_dashboard):
    server, service, _ = running_dashboard
    status, result, _ = request(server, "GET", "/api/ports?strat=3000")
    assert status == 400 and "Only start and end" in result["error"]
    assert service.ranges == []


@pytest.mark.parametrize("method", ["GET", "POST"])
@pytest.mark.parametrize("path", ["http://[", "http://example.com/api/ports", "not-a-local-path"])
def test_malformed_request_targets_return_json_bad_request(running_dashboard, method, path):
    server, _, _ = running_dashboard
    status, result, _ = request(
        server, method, path, headers={"Host": f"127.0.0.1:{server.server_port}"}
    )
    assert status == 400 and "request path is invalid" in result["error"]
