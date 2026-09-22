from portwatch.domain.exceptions import PortNotFoundError
from portwatch.domain.models import PortInfo
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

    def list_ports(self, port_range: tuple[int, int] | None = None) -> list[PortInfo]:
        ports = [self._enrich(item) for item in self.scanner.list_listening_ports()]
        if port_range is None:
            return ports
        start, end = port_range
        return [item for item in ports if start <= item.port <= end]

    def inspect(self, port: int) -> PortInfo:
        validate_port(port)
        for item in self.list_ports():
            if item.port == port:
                return item
        raise PortNotFoundError(f"Port {port} is available.")

    def next_available(self, start: int) -> int:
        validate_port(start)
        occupied = {item.port for item in self.list_ports()}
        for port in range(start, 65536):
            if port not in occupied:
                return port
        raise PortNotFoundError("No available port was found.")

    def _enrich(self, item: PortInfo) -> PortInfo:
        resolved = self.resolver.enrich(item)
        return PortInfo(
            port=resolved.port,
            protocol=resolved.protocol,
            status=resolved.status,
            pid=resolved.pid,
            process_name=resolved.process_name,
            command=resolved.command,
            working_directory=resolved.working_directory,
            project_name=self.project_detector.detect(resolved.working_directory),
            started_at=resolved.started_at,
        )
