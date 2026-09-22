from portwatch.presentation.console import format_port_count


def test_format_port_count_handles_singular() -> None:
    assert format_port_count(1) == "1 port listening"
    assert format_port_count(2) == "2 ports listening"
