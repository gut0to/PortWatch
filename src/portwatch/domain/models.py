from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class PortInfo:
    port: int
    protocol: str
    status: str
    pid: int | None = None
    process_name: str | None = None
    command: str | None = None
    working_directory: str | None = None
    project_name: str | None = None
    started_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class PortRange:
    start: int
    end: int

