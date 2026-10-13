from pathlib import Path

import pytest

from portwatch.services.project_detector import ProjectDetector


def test_project_detector_finds_marker_parent(tmp_path: Path) -> None:
    root = tmp_path / "backend"
    child = root / "src"
    child.mkdir(parents=True)
    (root / "pyproject.toml").touch()

    assert ProjectDetector().detect(str(child)) == "backend"


def test_project_detector_ignores_missing_directory(tmp_path: Path) -> None:
    assert ProjectDetector().detect(str(tmp_path / "missing")) is None


def test_project_detector_handles_filesystem_errors(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(Path, "is_dir", lambda self: (_ for _ in ()).throw(OSError("denied")))

    assert ProjectDetector().detect(str(tmp_path)) is None


def test_project_detector_returns_none_without_marker(tmp_path: Path) -> None:
    directory = tmp_path / "plain"
    directory.mkdir()

    assert ProjectDetector().detect(str(directory)) is None


@pytest.mark.parametrize(
    "marker",
    [
        "build.gradle.kts",
        "settings.gradle.kts",
        "deno.json",
        "deno.jsonc",
        "CMakeLists.txt",
        "Makefile",
    ],
)
def test_detects_additional_build_systems(tmp_path, marker):
    (tmp_path / marker).touch()
    assert ProjectDetector().detect(str(tmp_path)) == tmp_path.name


@pytest.mark.parametrize("marker", ["app.csproj", "app.fsproj", "app.sln", "app.slnx"])
def test_detects_dotnet_project_roots(tmp_path, marker):
    (tmp_path / marker).touch()
    assert ProjectDetector().detect(str(tmp_path)) == tmp_path.name
