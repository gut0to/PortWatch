import csv
import io
import json

import pytest
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


def test_csv_snapshot_round_trips_quoted_metadata_and_empty_cells():
    from portwatch.domain.models import PortInfo
    from portwatch.presentation.serializers import ports_to_csv
    from portwatch.services.snapshots import decode_csv_snapshot

    item = PortInfo(3000, "tcp", "LISTENING", command='python "a,b.py"')
    assert decode_csv_snapshot(ports_to_csv([item])) == [item]
    assert decode_csv_snapshot(ports_to_csv([])) == []


@pytest.mark.parametrize(
    "text",
    [
        "",
        "port,port,protocol,status\n",
        "port,protocol,status,bogus\n",
        "port,protocol,status\n1,tcp\n",
        "port,protocol,status\n1,tcp,LISTENING,extra\n",
        "port,protocol,status\nTrue,tcp,LISTENING\n",
        'port,protocol,status\n"unterminated',
        "port,protocol,status,pid\n1,tcp,LISTENING,-1\n",
    ],
)
def test_csv_snapshot_rejects_ambiguous_or_malformed_input(text):
    from portwatch.services.snapshots import decode_csv_snapshot

    with pytest.raises(ValueError):
        decode_csv_snapshot(text)


def test_csv_files_can_be_compared_as_snapshots(tmp_path):
    from portwatch.services.snapshots import load_snapshot

    path = tmp_path / "ports.CSV"
    path.write_text("port,protocol,status\n3000,tcp,LISTENING", encoding="utf-8-sig")
    assert load_snapshot(path)[0].port == 3000
    result = CliRunner().invoke(cli.app, ["diff", str(path), str(path), "--json"])
    assert result.exit_code == 0 and not any(json.loads(result.stdout).values())


def test_convert_snapshot_output_formats_and_invalid_input(tmp_path):
    path = tmp_path / "ports.csv"
    path.write_text("port,protocol,status\n3000,tcp,LISTENING")
    runner = CliRunner()
    for target in ("json", "jsonl", "csv"):
        result = runner.invoke(cli.app, ["convert", str(path), "--to", target])
        assert result.exit_code == 0 and "3000" in result.stdout
    path.write_text("bad")
    assert runner.invoke(cli.app, ["convert", str(path)]).exit_code == 2


def test_conversion_filters_and_redacts_before_export(tmp_path):
    path = tmp_path / "ports.json"
    path.write_text('[{"port":3000,"protocol":"tcp","status":"LISTENING","command":"secret"}]')
    args = ["convert", str(path), "--ports", "3000", "--search", "secret", "--redact"]
    result = CliRunner().invoke(cli.app, args)
    assert result.exit_code == 0 and json.loads(result.stdout)[0]["command"] is None
    assert CliRunner().invoke(cli.app, ["convert", str(path), "--ports", "bad"]).exit_code == 2
