"""Bound repeated scans independently of terminal presentation."""

import time
from collections.abc import Callable, Iterator

from portwatch.domain.models import PortInfo


def watch_snapshots(
    scan: Callable[[], list[PortInfo]],
    interval: float,
    count: int,
    *,
    changes_only: bool = False,
    sleep: Callable[[float], None] = time.sleep,
) -> Iterator[list[PortInfo]]:
    previous: frozenset[PortInfo] | None = None
    scans = 0
    while True:
        ports = scan()
        signature = frozenset(ports)
        if not changes_only or signature != previous:
            yield ports
        previous = signature
        scans += 1
        if count and scans >= count:
            return
        sleep(interval)
