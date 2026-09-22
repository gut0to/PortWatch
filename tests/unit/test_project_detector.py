from pathlib import Path

from portwatch.services.project_detector import ProjectDetector


def test_project_detector_finds_marker_parent(tmp_path: Path) -> None:
    root = tmp_path / "backend"
    child = root / "src"
    child.mkdir(parents=True)
    (root / "pyproject.toml").touch()

    assert ProjectDetector().detect(str(child)) == "backend"


def test_project_detector_ignores_missing_directory(tmp_path: Path) -> None:
    assert ProjectDetector().detect(str(tmp_path / "missing")) is None
