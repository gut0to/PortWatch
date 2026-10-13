"""Pure filtering shared by scripted listener queries."""

from portwatch.domain.models import PortInfo


def filter_ports(
    ports: list[PortInfo], query: str = "", *, pid: int | None = None, process: str = ""
) -> list[PortInfo]:
    ports = [item for item in ports if pid is None or item.pid == pid]
    if process.strip():
        ports = [
            item
            for item in ports
            if process.strip().casefold() in (item.process_name or "").casefold()
        ]
    needle = query.strip().casefold()
    return [
        item
        for item in ports
        if not needle
        or any(
            needle in str(value).casefold()
            for value in (
                item.port,
                item.pid,
                item.process_name,
                item.project_name,
                item.command,
                item.working_directory,
                item.protocol,
                item.status,
            )
            if value is not None
        )
    ]
