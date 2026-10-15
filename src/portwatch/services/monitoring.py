"""Bound repeated scans independently of terminal presentation."""

import time
from collections.abc import Callable, Iterator

from portwatch.domain.models import PortInfo


def watch_snapshots(
    scan: Callable[[], list[PortInfo]],
    interval: float,
    count: int,
    *,
    sleep: Callable[[float], None] = time.sleep,
) -> Iterator[list[PortInfo]]:
    scans = 0
    while True:
        yield scan()
        scans += 1
        if count and scans >= count:
            return
        sleep(interval)
