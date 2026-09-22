from datetime import datetime

from portwatch.domain.models import PortInfo
from portwatch.presentation.serializers import ports_to_json


def test_ports_to_json_is_predictable() -> None:
    result = ports_to_json([PortInfo(3000, "tcp", "LISTENING", pid=42)])

    assert '"port": 3000' in result
    assert '"protocol": "tcp"' in result


def test_ports_to_json_serializes_start_time() -> None:
    result = ports_to_json([PortInfo(3000, "tcp", "LISTENING", started_at=datetime(2024, 1, 1))])

    assert "2024-01-01T00:00:00" in result
