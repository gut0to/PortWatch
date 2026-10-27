"""Bound repeated scans independently of terminal presentation."""

import math
import time
from collections.abc import Callable, Iterator

from portwatch.domain.models import PortInfo


def watch_snapshots(
    scan: Callable[[], list[PortInfo]],
    interval: float,
    count: int,
    *,
    duration: float | None = None,
    clock: Callable[[], float] = time.monotonic,
    changes_only: bool = False,
    skip_initial: bool = False,
    sleep: Callable[[float], None] = time.sleep,
) -> Iterator[list[PortInfo]]:
    if not math.isfinite(interval) or interval < 0.2:
        raise ValueError("Watch interval must be finite and at least 0.2 seconds.")
    if isinstance(count, bool) or not isinstance(count, int) or count < 0:
        raise ValueError("Watch count must be a nonnegative integer.")
    if duration is not None and (not math.isfinite(duration) or duration <= 0):
        raise ValueError("Watch duration must be finite and positive.")
    deadline = clock() + duration if duration is not None else None
    previous: frozenset[PortInfo] | None = None
    scans = 0
    while True:
        if deadline is not None and clock() >= deadline:
            return
        ports = scan()
        signature = frozenset(ports)
        if (not skip_initial or scans > 0) and (not changes_only or signature != previous):
            yield ports
        previous = signature
        scans += 1
        if count and scans >= count:
            return
        delay = interval if deadline is None else min(interval, max(0.0, deadline - clock()))
        if delay > 0:
            sleep(delay)
