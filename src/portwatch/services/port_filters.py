"""Pure listener filtering for terminal queries and monitoring."""

from portwatch.domain.models import PortInfo


def filter_ports(
    ports: list[PortInfo],
    query: str = "",
    *,
    pid: int | None = None,
    process: str = "",
    project: str = "",
) -> list[PortInfo]:
    matches = [item for item in ports if pid is None or item.pid == pid]
    for field, value in (("process_name", process), ("project_name", project)):
        needle = value.strip().casefold()
        if needle:
            matches = [
                item for item in matches if needle in (getattr(item, field) or "").casefold()
            ]
    terms = query.casefold().split()
    return [item for item in matches if _matches_terms(item, terms)]


def _matches_terms(item: PortInfo, terms: list[str]) -> bool:
    values = [
        str(value).casefold()
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
    ]
    return all(any(term in value for value in values) for term in terms)
