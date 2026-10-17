from portwatch.domain.exceptions import InvalidPortError, PortNotFoundError
from portwatch.domain.models import PortInfo, PortRange
from portwatch.system.network import NetworkScanner, PsutilNetworkScanner
from portwatch.system.processes import ProcessResolver, PsutilProcessResolver
from portwatch.utils.ports import validate_port

from .project_detector import ProjectDetector


class PortService:
    def __init__(
        self,
        scanner: NetworkScanner | None = None,
        resolver: ProcessResolver | None = None,
        project_detector: ProjectDetector | None = None,
    ) -> None:
        self.scanner = scanner or PsutilNetworkScanner()
        self.resolver = resolver or PsutilProcessResolver()
        self.project_detector = project_detector or ProjectDetector()

    def list_ports(self, port_range: PortRange | None = None) -> list[PortInfo]:
        ports = self.scanner.list_listening_ports()
        if port_range is not None:
            ports = [item for item in ports if port_range.start <= item.port <= port_range.end]
        projects: dict[str | None, str | None] = {}
        return [self._enrich(item, projects) for item in ports]

    def inspect(self, port: int) -> PortInfo:
        validate_port(port)
        for item in self.scanner.list_listening_ports():
            if item.port == port:
                return self._enrich(item)
        raise PortNotFoundError(f"Port {port} is available.")

    def next_available(self, start: int, end: int = 65535) -> int:
        return self.available_ports(start, 1, end)[0]

    def available_ports(
        self, start: int, count: int, end: int = 65535, *, excluded: frozenset[int] = frozenset()
    ) -> list[int]:
        bounds = PortRange(start, end)
        if isinstance(count, bool) or not isinstance(count, int) or count < 1:
            raise InvalidPortError("Available port count must be a positive integer.")
        found: list[int] = []
        occupied = {item.port for item in self.scanner.list_listening_ports()} | excluded
        for port in range(bounds.start, bounds.end + 1):
            if port not in occupied:
                found.append(port)
                if len(found) == count:
                    return found
        raise PortNotFoundError("Not enough available ports were found.")

    def _enrich(
        self, item: PortInfo, projects: dict[str | None, str | None] | None = None
    ) -> PortInfo:
        resolved = self.resolver.enrich(item)
        cache = projects if projects is not None else {}
        directory = resolved.working_directory
        if directory not in cache:
            cache[directory] = self.project_detector.detect(directory)
        return PortInfo(
            port=resolved.port,
            protocol=resolved.protocol,
            status=resolved.status,
            pid=resolved.pid,
            process_name=resolved.process_name,
            command=resolved.command,
            working_directory=resolved.working_directory,
            project_name=cache[directory],
            started_at=resolved.started_at,
        )
