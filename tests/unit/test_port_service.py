from unittest.mock import Mock

import pytest

from portwatch.domain.exceptions import PortNotFoundError
from portwatch.domain.models import PortInfo, PortRange
from portwatch.services.port_service import PortService


def test_list_ports_applies_domain_range() -> None:
    scanner = Mock()
    scanner.list_listening_ports.return_value = [
        PortInfo(3000, "tcp", "LISTENING"),
        PortInfo(9000, "tcp", "LISTENING"),
    ]
    resolver = Mock()
    resolver.enrich.side_effect = lambda item: item

    result = PortService(scanner=scanner, resolver=resolver).list_ports(PortRange(3000, 3000))

    assert [item.port for item in result] == [3000]


def test_next_available_skips_occupied_ports() -> None:
    scanner = Mock()
    scanner.list_listening_ports.return_value = [
        PortInfo(3000, "tcp", "LISTENING"),
        PortInfo(3001, "tcp", "LISTENING"),
    ]
    resolver = Mock()
    resolver.enrich.side_effect = lambda item: item

    result = PortService(scanner=scanner, resolver=resolver).next_available(3000)

    assert result == 3002


def test_service_enriches_project_and_rejects_exhausted_ports() -> None:
    scanner = Mock()
    scanner.list_listening_ports.return_value = [PortInfo(65535, "tcp", "LISTENING")]
    resolver = Mock()
    resolver.enrich.side_effect = lambda item: item
    detector = Mock()
    detector.detect.return_value = "backend"
    service = PortService(scanner=scanner, resolver=resolver, project_detector=detector)

    enriched = service.list_ports()[0]
    assert enriched.project_name == "backend"
    with pytest.raises(PortNotFoundError):
        service.next_available(65535)


def test_inspect_returns_matching_port_and_reports_available_port() -> None:
    scanner = Mock()
    scanner.list_listening_ports.return_value = [PortInfo(3000, "tcp", "LISTENING")]
    resolver = Mock()
    resolver.enrich.side_effect = lambda item: item
    service = PortService(scanner=scanner, resolver=resolver)

    assert service.inspect(3000).port == 3000
    with pytest.raises(PortNotFoundError):
        service.inspect(3001)


def test_range_does_not_resolve_excluded_processes():
    scanner = Mock()
    included = PortInfo(3000, "tcp", "LISTENING")
    scanner.list_listening_ports.return_value = [included, PortInfo(9000, "tcp", "LISTENING")]
    resolver = Mock()
    resolver.enrich.side_effect = lambda item: item
    PortService(scanner=scanner, resolver=resolver).list_ports(PortRange(3000, 3000))
    resolver.enrich.assert_called_once_with(included)


def test_inspect_resolves_only_requested_listener():
    scanner = Mock()
    scanner.list_listening_ports.return_value = [
        PortInfo(1, "tcp", "LISTENING"),
        PortInfo(2, "tcp", "LISTENING"),
    ]
    resolver = Mock()
    resolver.enrich.side_effect = lambda item: item
    assert PortService(scanner=scanner, resolver=resolver).inspect(2).port == 2
    assert resolver.enrich.call_count == 1


def test_next_available_never_reads_process_metadata():
    scanner = Mock()
    scanner.list_listening_ports.return_value = []
    resolver = Mock()
    assert PortService(scanner=scanner, resolver=resolver).next_available(3000) == 3000
    resolver.enrich.assert_not_called()
