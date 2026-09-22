import json
from dataclasses import asdict

from portwatch.domain.models import PortInfo


def port_to_dict(port: PortInfo) -> dict[str, object]:
    data = asdict(port)
    if port.started_at is not None:
        data["started_at"] = port.started_at.isoformat()
    return data


def ports_to_json(ports: list[PortInfo]) -> str:
    return json.dumps([port_to_dict(port) for port in ports], indent=2)
