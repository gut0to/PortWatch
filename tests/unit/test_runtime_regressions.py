"""Regression checks at the public command boundary."""

from unittest.mock import Mock

import pytest
from typer.testing import CliRunner

import portwatch.cli as cli
from portwatch.domain.exceptions import PermissionDeniedError, PortNotFoundError
from portwatch.domain.models import PortInfo


def test_missing_inspection_keeps_json_stdout_empty(monkeypatch) -> None:
    monkeypatch.setattr(cli.service, "inspect", Mock(side_effect=PortNotFoundError("available")))
    result = CliRunner().invoke(cli.app, ["inspect", "3000", "--json"])
    assert result.exit_code == 3
    assert result.stdout == ""
    assert "available" in result.stderr


def test_next_exhaustion_reports_a_stable_error(monkeypatch) -> None:
    monkeypatch.setattr(
        cli.service, "next_available", Mock(side_effect=PortNotFoundError("No available port"))
    )
    result = CliRunner().invoke(cli.app, ["next", "65535"])
    assert result.exit_code == 3
    assert "No available port" in result.stderr


@pytest.mark.parametrize(
    ("arguments", "method"),
    [
        (["list", "--json"], "list_ports"),
        (["inspect", "3000"], "inspect"),
        (["next", "3000"], "next_available"),
        (["watch"], "list_ports"),
        (["free", "3000", "--yes"], "inspect"),
    ],
)
@pytest.mark.parametrize(
    ("error", "code"), [(PermissionDeniedError("Denied"), 4), (OSError("Unavailable"), 1)]
)
def test_service_errors_are_reported_without_traceback(monkeypatch, arguments, method, error, code):
    monkeypatch.setattr(cli.service, method, Mock(side_effect=error))
    result = CliRunner().invoke(cli.app, arguments)
    assert result.exit_code == code
    assert str(error) in result.stderr
    assert "Traceback" not in result.stderr


@pytest.mark.parametrize(
    "replacement", [PortInfo(3000, "tcp", "LISTENING", pid=99), PortNotFoundError("available")]
)
def test_confirmation_does_not_terminate_a_changed_listener(monkeypatch, replacement):
    original = PortInfo(3000, "tcp", "LISTENING", pid=42)
    monkeypatch.setattr(cli.service, "inspect", Mock(side_effect=[original, replacement]))
    terminate = Mock()
    monkeypatch.setattr(cli.terminator, "terminate", terminate)
    result = CliRunner().invoke(cli.app, ["free", "3000"], input="y\n")
    terminate.assert_not_called()
    assert result.exit_code == 5
    assert "changed" in result.stderr
