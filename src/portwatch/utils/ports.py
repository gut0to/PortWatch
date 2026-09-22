from portwatch.domain.exceptions import InvalidPortError
from portwatch.domain.models import PortRange


def validate_port(port: int) -> int:
    if not 1 <= port <= 65535:
        raise InvalidPortError("Port must be between 1 and 65535.")
    return port


def parse_port_range(value: str) -> PortRange:
    parts = value.split("-", maxsplit=1)
    if len(parts) != 2 or not all(part.strip().isdigit() for part in parts):
        raise InvalidPortError("Range must use the format START-END, for example 3000-9000.")
    start, end = (int(part.strip()) for part in parts)
    validate_port(start)
    validate_port(end)
    if start > end:
        raise InvalidPortError("Range start must be less than or equal to its end.")
    return PortRange(start, end)
