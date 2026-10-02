"""Bound and normalize primitive values accepted by dashboard endpoints."""

from __future__ import annotations

MAX_REQUEST_BYTES = 4096
MAX_PORT = 65535


def single_port_parameter(parameters: dict[str, list[str]], key: str, default: str) -> str:
    """Require one decimal port parameter, falling back only when absent."""
    values = parameters.get(key, [default])
    if len(values) != 1 or not values[0].isdecimal():
        raise ValueError(f"{key.title()} must be a single port number.")
    return values[0]
