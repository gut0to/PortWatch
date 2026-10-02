"""Local dashboard request boundaries and browser-facing headers."""

from __future__ import annotations

import secrets
from urllib.parse import urlsplit

LOOPBACK_HOST = "127.0.0.1"
CONTENT_SECURITY_POLICY = (
    "default-src 'none'; script-src 'self'; style-src 'self'; "
    "connect-src 'self'; img-src 'self'; font-src 'self'; "
    "base-uri 'none'; form-action 'self'; frame-ancestors 'none'"
)
SECURITY_HEADERS = {
    "Cache-Control": "no-store",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Content-Security-Policy": CONTENT_SECURITY_POLICY,
}


def new_session_token() -> str:
    """Generate an unguessable token for state-changing requests in this run."""
    return secrets.token_urlsafe(32)


def expected_host(host_header: str, port: int) -> bool:
    """Accept only the exact loopback host and bound port."""
    try:
        host = urlsplit(f"//{host_header}")
        actual_port = host.port if host.port is not None else 80
    except ValueError:
        return False
    return (
        host.hostname == LOOPBACK_HOST
        and actual_port == port
        and host.username is None
        and host.path == ""
        and not host.query
        and not host.fragment
    )


def expected_origin(origin_header: str, host_header: str, port: int) -> bool:
    """Require a same-origin HTTP request to the exact local dashboard host."""
    try:
        origin = urlsplit(origin_header)
        actual_port = origin.port if origin.port is not None else 80
    except ValueError:
        return False
    return (
        expected_host(host_header, port)
        and origin.scheme == "http"
        and origin.hostname == LOOPBACK_HOST
        and actual_port == port
        and origin.username is None
        and origin.path in {"", "/"}
        and not origin.query
        and not origin.fragment
    )


def compare_session_token(candidate: str, expected: str) -> bool:
    """Compare request tokens without leaking comparison timing."""
    return candidate.isascii() and secrets.compare_digest(candidate, expected)
