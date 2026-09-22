import runpy
from unittest.mock import Mock


def test_module_entrypoint_invokes_app(monkeypatch) -> None:
    app = Mock()
    monkeypatch.setattr("portwatch.cli.app", app)

    runpy.run_module("portwatch.__main__", run_name="__main__")

    app.assert_called_once_with()
