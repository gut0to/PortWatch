from unittest.mock import Mock

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
