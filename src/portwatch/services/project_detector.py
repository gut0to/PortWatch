from pathlib import Path

PROJECT_MARKERS = (
    "pyproject.toml",
    "package.json",
    "Cargo.toml",
    "go.mod",
    "pom.xml",
    "build.gradle",
    "composer.json",
    "Gemfile",
    "docker-compose.yml",
    "docker-compose.yaml",
    "compose.yml",
    "compose.yaml",
    ".git",
)


class ProjectDetector:
    def detect(self, working_directory: str | None) -> str | None:
        if not working_directory:
            return None
        current = Path(working_directory)
        if not current.is_dir():
            return None
        for directory in (current, *current.parents):
            if any((directory / marker).exists() for marker in PROJECT_MARKERS):
                return directory.name or str(directory)
        return None
