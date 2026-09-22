from datetime import datetime

from rich.console import Console

from portwatch.domain.models import PortInfo


def print_inspection(console: Console, item: PortInfo) -> None:
    console.print(f"[bold]Port {item.port}[/bold]\n")
    values = {
        "Status": item.status,
        "Protocol": item.protocol.upper(),
        "Process": item.process_name or "-",
        "PID": item.pid or "-",
        "Command": item.command or "-",
        "Directory": item.working_directory or "-",
        "Project": item.project_name or "-",
        "Started": format_started(item.started_at),
    }
    for label, value in values.items():
        console.print(f"[bold]{label:<12}[/bold] {value}")


def format_started(value: datetime | None) -> str:
    if value is None:
        return "-"
    elapsed = max(0, int((datetime.now() - value).total_seconds()))
    minutes, seconds = divmod(elapsed, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}h {minutes}m ago"
    if minutes:
        return f"{minutes}m ago"
    return f"{seconds}s ago"
