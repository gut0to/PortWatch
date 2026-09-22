from datetime import datetime
from typing import Protocol

import psutil

from portwatch.domain.models import PortInfo


class ProcessResolver(Protocol):
    def enrich(self, port: PortInfo) -> PortInfo: ...


class PsutilProcessResolver:
    def enrich(self, port: PortInfo) -> PortInfo:
        if port.pid is None:
            return port
        try:
            process = psutil.Process(port.pid)
            name = self._safe_name(process)
            command = self._safe_cmdline(process)
            working_directory = self._safe_cwd(process)
            started_at = self._safe_create_time(process)
            return PortInfo(
                port=port.port,
                protocol=port.protocol,
                status=port.status,
                pid=port.pid,
                process_name=name,
                command=command,
                working_directory=working_directory,
                project_name=port.project_name,
                started_at=started_at,
            )
        except (psutil.AccessDenied, psutil.NoSuchProcess, psutil.ZombieProcess):
            return port

    @staticmethod
    def _safe_name(process: psutil.Process) -> str | None:
        try:
            return process.name()
        except (psutil.AccessDenied, psutil.NoSuchProcess, psutil.ZombieProcess):
            return None

    @staticmethod
    def _safe_cmdline(process: psutil.Process) -> str | None:
        try:
            command = process.cmdline()
            return " ".join(command) if command else None
        except (psutil.AccessDenied, psutil.NoSuchProcess, psutil.ZombieProcess):
            return None

    @staticmethod
    def _safe_cwd(process: psutil.Process) -> str | None:
        try:
            return process.cwd()
        except (psutil.AccessDenied, psutil.NoSuchProcess, psutil.ZombieProcess):
            return None

    @staticmethod
    def _safe_create_time(process: psutil.Process) -> datetime | None:
        try:
            return datetime.fromtimestamp(process.create_time())
        except (psutil.AccessDenied, psutil.NoSuchProcess, psutil.ZombieProcess, OSError):
            return None
