
import pytest
from typer.testing import CliRunner

import portwatch.cli as cli
from portwatch.domain.exceptions import InvalidPortError
from portwatch.domain.models import PortInfo, PortRange


@pytest.mark.parametrize(
    "start,end", [(0, 1), (3, 2), (1, 65536), (True, 2), (1, False), (1.5, 2), (1, "2")]
)
def test_range_invariant(start, end):
    with pytest.raises(InvalidPortError):
        PortRange(start, end)


@pytest.fixture
def listeners(monkeypatch):
    items = [
        PortInfo(3000, "tcp", "LISTENING", pid=10, process_name="Python", project_name="API"),
        PortInfo(
            4000, "tcp", "LISTENING", pid=20, process_name="python-worker", project_name="api-tools"
        ),
        PortInfo(4000, "tcp", "LISTENING", pid=30, process_name="node"),
    ]
    monkeypatch.setattr(cli.service, "list_ports", lambda port_range=None: items)
    return items


def invoke(*args):
    result = CliRunner().invoke(cli.app, list(args))
    assert result.exit_code == 0, result.output
    return result.stdout
