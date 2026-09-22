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
