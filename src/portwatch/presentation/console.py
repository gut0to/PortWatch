from datetime import datetime

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from portwatch.domain.models import PortInfo


def print_inspection(console: Console, item: PortInfo) -> None:
    details = Table.grid(padding=(0, 2))
    details.add_column(style="bold bright_white", width=12)
    details.add_column(style="white")
    values = {
        "Status": f"[bold green]{item.status}[/bold green]",
        "Protocol": item.protocol.upper(),
        "Process": item.process_name or "-",
        "PID": item.pid or "-",
        "Command": item.command or "-",
        "Directory": item.working_directory or "-",
        "Project": item.project_name or "-",
        "Started": format_started(item.started_at),
    }
    for label, value in values.items():
        details.add_row(label, str(value))
    console.print(Panel(details, title=f"[bold cyan]Port {item.port}[/bold cyan]", border_style="cyan"))


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
