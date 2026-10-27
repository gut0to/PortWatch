import json
from unittest.mock import Mock

import pytest
from typer.testing import CliRunner

import portwatch.cli as cli


@pytest.fixture
def saved(tmp_path, monkeypatch):
    path = tmp_path / "ports.json"
    path.write_text(
        '[{"port":3000,"protocol":"tcp","status":"LISTENING","pid":42},{"port":4000,"protocol":"tcp","status":"LISTENING","pid":43}]'
    )
    monkeypatch.setattr(
        cli.service, "list_ports", Mock(side_effect=AssertionError("offline command scanned"))
    )
    return path


def test_list_uses_saved_snapshot_with_range_and_output_formats(saved):
    result = CliRunner().invoke(
        cli.app, ["list", "--input", str(saved), "--range", "3000-3000", "--json"]
    )
    assert result.exit_code == 0
    assert [row["port"] for row in json.loads(result.stdout)] == [3000]
    assert (
        CliRunner().invoke(cli.app, ["list", "--input", str(saved), "--quiet"]).stdout
        == "3000\n4000\n"
    )
    saved.write_text("bad")
    assert CliRunner().invoke(cli.app, ["list", "--input", str(saved)]).exit_code == 2


def test_summary_operates_on_saved_snapshots(saved):
    result = CliRunner().invoke(
        cli.app, ["summary", "--input", str(saved), "--group", "process", "--json"]
    )
    assert result.exit_code == 0 and json.loads(result.stdout)["listeners"] == 2
    saved.write_text("bad")
    assert CliRunner().invoke(cli.app, ["summary", "--input", str(saved)]).exit_code == 2


def test_inspection_uses_snapshot_owners_and_distinct_missing_code(saved):
    runner = CliRunner()
    result = runner.invoke(cli.app, ["inspect", "3000", "--input", str(saved), "--json"])
    assert result.exit_code == 0 and json.loads(result.stdout)["pid"] == 42
    assert (
        len(
            json.loads(
                runner.invoke(
                    cli.app, ["inspect", "3000", "--input", str(saved), "--all", "--json"]
                ).stdout
            )
        )
        == 1
    )
    assert runner.invoke(cli.app, ["inspect", "5000", "--input", str(saved)]).exit_code == 3
    assert runner.invoke(cli.app, ["inspect", "0", "--input", str(saved)]).exit_code == 2
