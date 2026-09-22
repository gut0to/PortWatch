from datetime import datetime, timedelta
from io import StringIO

from rich.console import Console

from portwatch.domain.models import PortInfo
from portwatch.presentation.console import format_port_count, format_started, print_inspection


def test_format_port_count_handles_singular() -> None:
    assert format_port_count(1) == "1 port listening"
    assert format_port_count(2) == "2 ports listening"


def test_format_started_covers_elapsed_time_units() -> None:
    assert format_started(None) == "-"
    assert "2h" in format_started(datetime.now() - timedelta(hours=2, minutes=3))
    assert "2m" in format_started(datetime.now() - timedelta(minutes=2, seconds=3))
    assert "3s" in format_started(datetime.now() - timedelta(seconds=3))


def test_print_inspection_renders_all_process_details() -> None:
    output = StringIO()
    console = Console(file=output, force_terminal=False)
    item = PortInfo(
        3000,
        "tcp",
        "LISTENING",
        pid=42,
        process_name="python.exe",
        command="python -m http.server",
        working_directory="C:/Projects/backend",
        project_name="backend",
        started_at=datetime.now() - timedelta(minutes=1),
    )

    print_inspection(console, item)

    rendered = output.getvalue()
    assert "Port 3000" in rendered
    assert "python.exe" in rendered
