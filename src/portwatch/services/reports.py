"""Aggregate listener snapshots without conflating sockets and processes."""

from portwatch.domain.models import PortInfo


def summarize_ports(ports: list[PortInfo]) -> dict[str, int]:
    return {
        "listeners": len(ports),
        "ports": len({item.port for item in ports}),
        "processes": len({item.pid for item in ports if item.pid is not None}),
        "projects": len({item.project_name for item in ports if item.project_name}),
        "unresolved": sum(item.pid is None for item in ports),
    }
