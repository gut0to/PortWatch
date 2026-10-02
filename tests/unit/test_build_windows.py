"""Verify the build gate without launching a bundler."""

from unittest.mock import Mock

import pytest

from scripts import build_windows


def test_build_rejects_32_bit_python_on_64_bit_windows(monkeypatch):
    monkeypatch.setattr(build_windows.sys, "platform", "win32")
    monkeypatch.setattr(build_windows.platform, "machine", lambda: "AMD64")
    monkeypatch.setattr("struct.calcsize", lambda _: 4)
    bundler = Mock(side_effect=RuntimeError("Bundler must not be reached"))
    monkeypatch.setattr(build_windows.subprocess, "run", bundler)
    with pytest.raises(SystemExit, match="64-bit Python"):
        build_windows.main()
    bundler.assert_not_called()
