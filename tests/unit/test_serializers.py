from portwatch.domain.models import PortInfo
from portwatch.presentation.serializers import ports_to_json


def test_ports_to_json_is_predictable() -> None:
    result = ports_to_json([PortInfo(3000, "tcp", "LISTENING", pid=42)])

    assert '"port": 3000' in result
    assert '"protocol": "tcp"' in result
