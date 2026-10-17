from dataclasses import replace
from unittest.mock import Mock

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
