import json
from dataclasses import replace
from unittest.mock import Mock

import pytest
from typer.testing import CliRunner

import portwatch.cli as cli
from portwatch.domain.models import PortInfo
from portwatch.services.snapshots import write_snapshot


def test_output_files_are_complete_and_require_explicit_overwrite(tmp_path):
    path = tmp_path / "ports.json"
    write_snapshot(path, "[]")
    with pytest.raises(FileExistsError):
        write_snapshot(path, "new")
    assert path.read_text(encoding="utf-8") == "[]\n"
    assert list(tmp_path.iterdir()) == [path]
    write_snapshot(path, "new", overwrite=True)
    assert path.read_text(encoding="utf-8") == "new\n"


def test_output_replace_failure_keeps_old_snapshot(tmp_path, monkeypatch):
    import portwatch.services.snapshots as snapshots

    path = tmp_path / "ports.json"
    path.write_text("old", encoding="utf-8")
    monkeypatch.setattr(snapshots.os, "replace", Mock(side_effect=OSError("locked")))
    with pytest.raises(OSError):
        write_snapshot(path, "new", overwrite=True)
    assert path.read_text() == "old"
    assert list(tmp_path.iterdir()) == [path]


def test_output_write_failure_cleans_temporary_file(tmp_path, monkeypatch):
    import portwatch.services.snapshots as snapshots

    real = snapshots.tempfile.NamedTemporaryFile

    def failing_file(**kwargs):
        handle = real(**kwargs)
        handle.write = Mock(side_effect=OSError("disk full"))
        return handle

    monkeypatch.setattr(snapshots.tempfile, "NamedTemporaryFile", failing_file)
    with pytest.raises(OSError, match="disk full"):
        write_snapshot(tmp_path / "ports.json", "[]")
    assert list(tmp_path.iterdir()) == []


def test_cli_snapshot_output_formats_and_overwrite(tmp_path, monkeypatch):
    monkeypatch.setattr(
        cli.service, "list_ports", lambda bounds=None: [PortInfo(3000, "tcp", "LISTENING")]
    )
    path = tmp_path / "ports.json"
    runner = CliRunner()
    result = runner.invoke(cli.app, ["list", "--output", str(path)])
    assert result.exit_code == 0
    assert result.stdout == ""
    assert json.loads(path.read_text())[0]["port"] == 3000
    assert runner.invoke(cli.app, ["list", "--output", str(path)]).exit_code == 2
    for flag in ("--csv", "--json-lines"):
        assert (
            runner.invoke(cli.app, ["list", "--output", str(path), "--overwrite", flag]).exit_code
            == 0
        )
    assert runner.invoke(cli.app, ["list", "--overwrite"]).exit_code == 2
    assert runner.invoke(cli.app, ["list", "--quiet", "--output", str(path)]).exit_code == 2


def test_redaction_preserves_identity_and_original_snapshot(monkeypatch):
    from portwatch.services.snapshots import redact_snapshot

    original = PortInfo(
        3000, "tcp", "LISTENING", pid=42, command="secret-token", working_directory="private"
    )
    assert redact_snapshot([original]) == [replace(original, command=None, working_directory=None)]
    monkeypatch.setattr(cli.service, "list_ports", lambda bounds=None: [original])
    result = CliRunner().invoke(cli.app, ["list", "--redact", "--json"])
    assert result.exit_code == 0
    assert "secret-token" not in result.stdout
    assert json.loads(result.stdout)[0]["pid"] == 42
    assert original.command == "secret-token"


@pytest.mark.parametrize("value", ["=SUM(1,2)", "+1", "-1", "@cmd", "  =1"])
def test_csv_metadata_cannot_be_evaluated_as_formulas(value):
    import csv
    import io

    from portwatch.presentation.serializers import ports_to_csv

    rows = list(
        csv.DictReader(io.StringIO(ports_to_csv([PortInfo(1, "tcp", "LISTENING", command=value)])))
    )
    assert rows[0]["command"] == "'" + value


def test_tables_preserve_literal_process_and_project_markup():
    from io import StringIO

    from rich.console import Console

    from portwatch.presentation.tables import ports_table

    output = StringIO()
    Console(file=output, width=140, color_system=None).print(
        ports_table(
            [
                PortInfo(
                    3000,
                    "tcp",
                    "LISTENING",
                    process_name="[bold]worker[/bold]",
                    project_name="[red]api[/red]",
                )
            ]
        )
    )
    assert "[bold]worker[/bold]" in output.getvalue()
    assert "[red]api[/red]" in output.getvalue()


def test_termination_confirmation_preserves_literal_names(monkeypatch):
    monkeypatch.setattr(
        cli.service,
        "inspect",
        lambda port: PortInfo(
            port,
            "tcp",
            "LISTENING",
            pid=42,
            process_name="[red]worker[/red]",
            project_name="[bold]api[/bold]",
        ),
    )
    result = CliRunner().invoke(cli.app, ["free", "3000"], input="n\n")
    assert result.exit_code == 0
    assert "[red]worker[/red]" in result.stdout
    assert "[bold]api[/bold]" in result.stdout
