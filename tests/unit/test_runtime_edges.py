from unittest.mock import Mock

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


def test_project_markers_must_be_files_except_git_directories(tmp_path):
    from portwatch.services.project_detector import ProjectDetector

    (tmp_path / "package.json").mkdir()
    assert ProjectDetector().detect(str(tmp_path)) is None
    (tmp_path / ".git").mkdir()
    assert ProjectDetector().detect(str(tmp_path)) == tmp_path.name


def test_snapshot_data_is_synced_before_publication_and_failures_do_not_replace_old_data(
    tmp_path, monkeypatch
):
    import portwatch.services.snapshots as snapshots

    path = tmp_path / "ports.json"
    path.write_text("old")
    sync = Mock(side_effect=OSError("sync failed"))
    monkeypatch.setattr(snapshots.os, "fsync", sync)
    with pytest.raises(OSError, match="sync failed"):
        snapshots.write_snapshot(path, "[]", overwrite=True)
    assert path.read_text() == "old"
    assert list(tmp_path.iterdir()) == [path]
    sync.assert_called_once()


def test_version_is_available_even_when_a_subcommand_is_missing_arguments():
    from typer.testing import CliRunner

    import portwatch.cli as cli

    for command in ("inspect", "diff", "history", "check"):
        result = CliRunner().invoke(cli.app, ["--version", command])
        assert result.exit_code == 0 and result.stdout.startswith("PortWatch ")
