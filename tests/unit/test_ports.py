import pytest

from portwatch.domain.exceptions import InvalidPortError
from portwatch.utils.ports import parse_port_range, validate_port


def test_validate_port_accepts_boundaries() -> None:
    assert validate_port(1) == 1
    assert validate_port(65535) == 65535


@pytest.mark.parametrize("value", [0, 65536, -1])
def test_validate_port_rejects_out_of_range(value: int) -> None:
    with pytest.raises(InvalidPortError):
        validate_port(value)


def test_parse_port_range() -> None:
    assert parse_port_range("3000-9000").start == 3000
    assert parse_port_range("3000 - 9000").end == 9000


@pytest.mark.parametrize("value", ["3000", "9000-3000", "x-9000", "1-70000"])
def test_parse_port_range_rejects_invalid_values(value: str) -> None:
    with pytest.raises(InvalidPortError):
        parse_port_range(value)
