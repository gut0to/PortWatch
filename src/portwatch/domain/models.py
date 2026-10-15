from dataclasses import dataclass
from datetime import datetime

from portwatch.domain.exceptions import InvalidPortError


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

    def __post_init__(self) -> None:
        if (
            isinstance(self.start, bool)
            or isinstance(self.end, bool)
            or not isinstance(self.start, int)
            or not isinstance(self.end, int)
            or not 1 <= self.start <= self.end <= 65535
        ):
            raise InvalidPortError("Port ranges must satisfy 1 <= start <= end <= 65535.")
