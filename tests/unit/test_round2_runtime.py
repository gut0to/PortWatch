from types import SimpleNamespace
from unittest.mock import Mock

import pytest

import portwatch.system.processes as processes
from portwatch.system.processes import PsutilProcessResolver


@pytest.mark.parametrize("platform", ["nt", "posix"])
def test_command_display_quotes_argument_boundaries(monkeypatch, platform):
    import shlex
    import subprocess

    monkeypatch.setattr(processes, "os", SimpleNamespace(name=platform))
    process = Mock()
    process.cmdline.return_value = ["python", "folder with spaces/server.py", "--token=a b"]
    expected = (
        subprocess.list2cmdline(process.cmdline.return_value)
        if platform == "nt"
        else shlex.join(process.cmdline.return_value)
    )
    assert PsutilProcessResolver._safe_cmdline(process) == expected
    process.cmdline.return_value = []
    assert PsutilProcessResolver._safe_cmdline(process) is None


@pytest.mark.parametrize("timestamp", [float("nan"), float("inf"), float("-inf"), 1e50])
def test_invalid_process_timestamps_do_not_abort_scan(timestamp):
    process = Mock()
    process.create_time.return_value = timestamp
    assert PsutilProcessResolver._safe_create_time(process) is None
