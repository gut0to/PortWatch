from rich.table import Table

from portwatch.domain.models import PortInfo


def ports_table(ports: list[PortInfo]) -> Table:
    table = Table(title="PORTWATCH")
    for column in ("PORT", "PROTOCOL", "PID", "PROCESS", "PROJECT"):
        table.add_column(column)
    for item in ports:
        table.add_row(
            str(item.port),
            item.protocol.upper(),
            str(item.pid or "-"),
            item.process_name or "-",
            item.project_name or "-",
        )
    return table
