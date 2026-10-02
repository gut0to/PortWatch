"""Resolve bundled dashboard assets without exposing files outside their root."""

from __future__ import annotations

import mimetypes
import sys
from pathlib import Path
from urllib.parse import unquote

STATIC_DIRECTORY = Path(__file__).parent / "static"


def static_directory() -> Path:
    """Resolve the static directory from source or a frozen executable bundle."""
    if getattr(sys, "frozen", False):
        bundle_root = Path(vars(sys)["_MEIPASS"])
        return bundle_root / "portwatch" / "web" / "static"
    return STATIC_DIRECTORY


def read_static_asset(request_path: str) -> tuple[str, bytes]:
    """Return an asset's MIME type and bytes, rejecting paths outside the bundle."""
    relative_path = unquote(request_path).lstrip("/") or "index.html"
    root = static_directory().resolve(strict=True)
    target = (root / relative_path).resolve(strict=True)
    if not target.is_relative_to(root) or not target.is_file():
        raise OSError("Not a file inside the dashboard directory.")

    content_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
    if content_type.startswith("text/") or content_type in {
        "application/javascript",
        "application/json",
    }:
        content_type = f"{content_type}; charset=utf-8"
    return content_type, target.read_bytes()
