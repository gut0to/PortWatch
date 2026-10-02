import runpy
import sys
from unittest.mock import Mock

import pytest


def test_module_entrypoint_invokes_app(monkeypatch) -> None:
    app = Mock()
    monkeypatch.setattr("portwatch.cli.app", app)

    runpy.run_module("portwatch.__main__", run_name="__main__")

    app.assert_called_once_with()


@pytest.mark.parametrize(
    ("arguments", "expected"),
    [(["portwatch.exe"], ["dashboard"]), (["portwatch.exe", "list"], None)],
)
def test_frozen_entrypoint_launches_dashboard_only_without_arguments(monkeypatch, arguments, expected):
    app = Mock()
    monkeypatch.setattr("portwatch.cli.app", app)
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "argv", arguments)
    runpy.run_module("portwatch.__main__", run_name="__main__")
    if expected is None:
        app.assert_called_once_with()
    else:
        app.assert_called_once_with(args=expected)
