"""Run PortWatch as a module."""

import sys

from portwatch.cli import app

if __name__ == "__main__":  # pragma: no branch
    if getattr(sys, "frozen", False) and len(sys.argv) == 1:
        app(args=["dashboard"])
    else:
        app()
