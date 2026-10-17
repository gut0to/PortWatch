from dataclasses import replace
from unittest.mock import Mock

import pytest

from portwatch.domain.models import PortInfo
from portwatch.services.port_service import PortService


def test_project_detection_is_cached_only_within_one_scan():
    scanner = Mock()
    scanner.list_listening_ports.return_value = [
        PortInfo(3000, "tcp", "LISTENING", pid=1),
        PortInfo(3001, "tcp", "LISTENING", pid=2),
    ]
    resolver = Mock()
    resolver.enrich.side_effect = lambda item: replace(item, working_directory="root")
    detector = Mock()
    detector.detect.return_value = "API"
    service = PortService(scanner, resolver, detector)
    assert [item.project_name for item in service.list_ports()] == ["API", "API"]
    detector.detect.assert_called_once_with("root")
    detector.detect.return_value = "changed"
    assert service.list_ports()[0].project_name == "changed"
    assert detector.detect.call_count == 2


def test_inspect_all_preserves_distinct_owners_and_resolves_only_one_port():
    from portwatch.domain.exceptions import InvalidPortError, PortNotFoundError

    scanner = Mock()
    scanner.list_listening_ports.return_value = [
        PortInfo(3000, "tcp", "LISTENING", pid=1),
        PortInfo(3000, "tcp", "LISTENING", pid=2),
        PortInfo(4000, "tcp", "LISTENING", pid=3),
    ]
    resolver = Mock()
    resolver.enrich.side_effect = lambda item: item
    service = PortService(scanner, resolver)
    assert [item.pid for item in service.inspect_all(3000)] == [1, 2]
    assert resolver.enrich.call_count == 2
    with pytest.raises(InvalidPortError):
        service.inspect_all(0)
    with pytest.raises(PortNotFoundError):
        service.inspect_all(3001)


def test_cli_inspect_all_keeps_single_owner_contract(monkeypatch):
    import json

    from typer.testing import CliRunner

    import portwatch.cli as cli

    items = [PortInfo(3000, "tcp", "LISTENING", pid=1), PortInfo(3000, "tcp", "LISTENING", pid=2)]
    monkeypatch.setattr(cli.service, "inspect_all", lambda port: items)
    monkeypatch.setattr(cli.service, "inspect", lambda port: items[0])
    runner = CliRunner()
    result = runner.invoke(cli.app, ["inspect", "3000", "--all", "--json"])
    assert result.exit_code == 0
    assert [item["pid"] for item in json.loads(result.stdout)] == [1, 2]
    assert json.loads(runner.invoke(cli.app, ["inspect", "3000", "--json"]).stdout)["pid"] == 1
    assert runner.invoke(cli.app, ["inspect", "3000", "--all"]).exit_code == 0
