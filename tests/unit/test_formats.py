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
