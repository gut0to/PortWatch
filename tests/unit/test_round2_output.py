import json
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
