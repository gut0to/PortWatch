import json
from dataclasses import replace

import pytest
from typer.testing import CliRunner

import portwatch.cli as cli
from portwatch.domain.models import PortInfo
from portwatch.presentation.serializers import port_to_dict


@pytest.fixture
def files(tmp_path):
    old = [
        PortInfo(
            3000,
            "tcp",
            "LISTENING",
            pid=42,
            process_name="python",
            command="old",
            working_directory="private",
        ),
        PortInfo(4000, "tcp", "LISTENING", pid=43, process_name="worker"),
    ]
    new = [
        replace(old[0], command="new"),
        PortInfo(5000, "tcp", "LISTENING", pid=44, process_name="node"),
    ]
    paths = [tmp_path / "before.json", tmp_path / "after.json"]
    for path, items in zip(paths, [old, new], strict=True):
        path.write_text(json.dumps([port_to_dict(item) for item in items]), encoding="utf-8")
    return [str(path) for path in paths]


def invoke(files, *options):
    return CliRunner().invoke(cli.app, ["diff", *files, *options])


def test_diff_ignore_metadata_fields(files):
    result = invoke(files, "--ignore", "command", "--json")
    assert result.exit_code == 0
    assert json.loads(result.stdout)["changed"] == []
    assert invoke(files, "--ignore", "pid").exit_code == 2


def test_diff_port_selection_applies_to_both_snapshots(files):
    result = invoke(files, "--ports", "3000", "--json")
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["added"] == data["removed"] == []
    assert len(data["changed"]) == 1
    assert invoke(files, "--ports", "0").exit_code == 2


def test_diff_metadata_search(files):
    result = invoke(files, "--search", "python -worker", "--json")
    data = json.loads(result.stdout)
    assert data["added"] == data["removed"] == []
    assert len(data["changed"]) == 1


def test_diff_output_file_and_difference_exit_code(files, tmp_path):
    path = tmp_path / "changes.json"
    result = invoke(files, "--output", str(path), "--exit-code")
    assert result.exit_code == 6 and result.stdout == ""
    assert len(json.loads(path.read_text())["changed"]) == 1
    assert invoke(files, "--output", str(path)).exit_code == 2
    assert invoke(files, "--output", str(path), "--overwrite").exit_code == 0
    assert invoke(files, "--overwrite").exit_code == 2


def test_diff_redaction_keeps_sensitive_changes_visible(files):
    result = invoke(files, "--redact", "--json")
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert len(data["changed"]) == 1
    assert data["changed"][0]["before"]["command"] is None
    assert "private" not in result.stdout
    assert data["added"][0]["command"] is None


def test_csv_changes_preserve_before_and_after_and_escape_formulas():
    import csv
    import io

    from portwatch.presentation.serializers import changes_to_csv

    row = {"port": 1, "command": "=1"}
    rows = list(
        csv.DictReader(
            io.StringIO(
                changes_to_csv({"changed": [{"before": row, "after": row}], "added": [row]})
            )
        )
    )
    assert [item["side"] for item in rows] == ["before", "after", "listener"]
    assert all(item["command"] == "'=1" for item in rows)
    assert "change,side,port" in changes_to_csv({})


def test_cli_diff_csv_stdout_and_file(files, tmp_path):
    result = invoke(files, "--csv")
    assert result.exit_code == 0 and result.stdout.startswith("change,side,port,")
    path = tmp_path / "changes.csv"
    assert invoke(files, "--csv", "--output", str(path)).exit_code == 0
    assert "changed,before,3000" in path.read_text()
    assert invoke(files, "--csv", "--json").exit_code == 2
