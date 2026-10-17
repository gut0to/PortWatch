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
