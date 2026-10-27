from unittest.mock import Mock

import pytest

from portwatch.domain.exceptions import InvalidPortError, PortNotFoundError
from portwatch.domain.models import PortInfo
from portwatch.services.port_service import PortService


def test_available_port_blocks_do_not_bridge_busy_or_reserved_ports():
    scanner = Mock()
    scanner.list_listening_ports.return_value = [PortInfo(3001, "tcp", "LISTENING")]
    service = PortService(scanner=scanner)
    assert service.available_port_block(3000, 2, 3005, excluded=frozenset({3003})) == [3004, 3005]
    with pytest.raises(PortNotFoundError):
        service.available_port_block(3000, 3, 3003)
    for count in (0, True):
        with pytest.raises(InvalidPortError):
            service.available_port_block(3000, count)


def test_cli_requests_contiguous_ports_and_keeps_batch_json(monkeypatch):
    import json

    from typer.testing import CliRunner

    import portwatch.cli as cli

    scanner = Mock()
    scanner.list_listening_ports.return_value = [PortInfo(3001, "tcp", "LISTENING")]
    monkeypatch.setattr(cli, "service", PortService(scanner=scanner))
    result = CliRunner().invoke(cli.app, ["next", "3000", "--count", "2", "--contiguous", "--json"])
    assert result.exit_code == 0 and json.loads(result.stdout)["ports"] == [3002, 3003]
