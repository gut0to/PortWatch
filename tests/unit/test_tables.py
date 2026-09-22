from portwatch.domain.models import PortInfo
from portwatch.presentation.tables import ports_table


def test_ports_table_contains_readable_columns() -> None:
    table = ports_table([PortInfo(3000, "tcp", "LISTENING", pid=42, process_name="python")])

    assert [column.header for column in table.columns] == [
        "PORT",
        "PROTOCOL",
        "PID",
        "PROCESS",
        "PROJECT",
    ]
