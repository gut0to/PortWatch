"""Regression checks at the public command boundary."""

from unittest.mock import Mock

from typer.testing import CliRunner

import portwatch.cli as cli
from portwatch.domain.exceptions import PortNotFoundError


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
