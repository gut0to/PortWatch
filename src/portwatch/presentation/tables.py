from rich.box import ROUNDED
from rich.table import Table

from portwatch.domain.models import PortInfo


def ports_table(ports: list[PortInfo]) -> Table:
    table = Table(
        title="[bold cyan]PORTWATCH[/bold cyan]",
        caption="Listening TCP ports",
        box=ROUNDED,
        header_style="bold bright_white on dark_cyan",
        border_style="cyan",
        show_lines=False,
        padding=(0, 1),
    )
    table.add_column("PORT", justify="right", style="bold cyan", no_wrap=True)
    table.add_column("PROTOCOL", style="bright_white", no_wrap=True)
    table.add_column("PID", justify="right", style="yellow", no_wrap=True)
    table.add_column("PROCESS", style="white")
    table.add_column("PROJECT", style="bright_green")
    for item in ports:
        table.add_row(
            str(item.port),
            item.protocol.upper(),
            str(item.pid or "-"),
            item.process_name or "-",
            item.project_name or "-",
        )
    return table
