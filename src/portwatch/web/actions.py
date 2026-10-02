"""Dashboard actions with a fresh listener check before termination."""

from __future__ import annotations

from portwatch.services.port_service import PortService
from portwatch.system.termination import ProcessTerminator


class StaleListenerError(RuntimeError):
    """The requested port no longer belongs to the process shown in the UI."""


def terminate_listener(
    service: PortService,
    terminator: ProcessTerminator,
    port: int,
    pid: int,
) -> str:
    """Recheck the port/PID pair immediately before requesting process exit."""
    current_ports = service.list_ports()
    if any(item.port == port and item.pid == pid for item in current_ports):
        terminator.terminate(pid)
        return f"Process {pid} was asked to stop."

    same_port = any(item.port == port for item in current_ports)
    if same_port:
        raise StaleListenerError("The process using this port changed. Rescan before trying again.")
    raise StaleListenerError(f"Port {port} is no longer listening. Rescan before trying again.")
