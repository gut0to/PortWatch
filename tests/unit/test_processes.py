from unittest.mock import Mock

import psutil

from portwatch.domain.models import PortInfo
from portwatch.system.processes import PsutilProcessResolver


def test_process_resolver_keeps_port_when_process_disappears(monkeypatch) -> None:
    monkeypatch.setattr(
        "portwatch.system.processes.psutil.Process",
        Mock(side_effect=psutil.NoSuchProcess(123)),
    )
    port = PortInfo(3000, "tcp", "LISTENING", pid=123)

    assert PsutilProcessResolver().enrich(port) == port


def test_process_resolver_enriches_available_metadata(monkeypatch) -> None:
    process = Mock()
    process.name.return_value = "python.exe"
    process.cmdline.return_value = ["python", "-m", "http.server"]
    process.cwd.return_value = "C:/Projects/backend"
    process.create_time.return_value = 1_700_000_000
    monkeypatch.setattr("portwatch.system.processes.psutil.Process", Mock(return_value=process))

    result = PsutilProcessResolver().enrich(PortInfo(8000, "tcp", "LISTENING", pid=123))

    assert result.process_name == "python.exe"
    assert result.command == "python -m http.server"
    assert result.working_directory == "C:/Projects/backend"
    assert result.started_at is not None
