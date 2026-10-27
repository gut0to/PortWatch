import csv
import io
import json

from typer.testing import CliRunner

import portwatch.cli as cli


def log_line():
    return json.dumps(
        {
            "scanned_at": "2026-10-27T12:00:00Z",
            "ports": [{"port": 3000, "protocol": "tcp", "status": "LISTENING"}],
        }
    )


def test_history_csv_contains_per_scan_counts(tmp_path):
    path = tmp_path / "watch.jsonl"
    path.write_text(log_line())
    result = CliRunner().invoke(cli.app, ["history", str(path), "--csv"])
    assert result.exit_code == 0
    assert list(csv.DictReader(io.StringIO(result.stdout)))[0]["listeners"] == "1"
    assert CliRunner().invoke(cli.app, ["history", str(path), "--csv", "--events"]).exit_code == 2


def test_history_reports_are_saved_without_accidental_replacement(tmp_path):
    path = tmp_path / "watch.jsonl"
    path.write_text(log_line())
    output = tmp_path / "report.json"
    runner = CliRunner()
    args = ["history", str(path), "--output", str(output)]
    assert runner.invoke(cli.app, args).stdout == ""
    assert json.loads(output.read_text())["scans"] == 1
    assert runner.invoke(cli.app, args).exit_code == 2
    assert runner.invoke(cli.app, [*args, "--overwrite", "--csv"]).exit_code == 0
    assert runner.invoke(cli.app, ["history", str(path), "--overwrite"]).exit_code == 2
