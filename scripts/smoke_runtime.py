"""Exercise installed or bundled PortWatch against real loopback listeners."""

from __future__ import annotations

import argparse
import json
import re
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import psutil


def stop_child(process: subprocess.Popen[str]) -> None:
    """Clean up only the child tree created by this smoke test."""
    try:
        children = psutil.Process(process.pid).children(recursive=True)
    except psutil.NoSuchProcess:
        children = []
    for child in reversed(children):
        try:
            child.terminate()
        except psutil.NoSuchProcess:
            pass
    if process.poll() is None:
        process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)
    _, alive = psutil.wait_procs(children, timeout=5)
    for child in alive:
        child.kill()


def verify_runtime(command: list[str]) -> None:
    """Run from an unrelated directory so source assets cannot hide packaging bugs."""
    with tempfile.TemporaryDirectory(prefix="portwatch-smoke-") as working_directory:

        def run(*arguments: str, expected: int = 0) -> str:
            result = subprocess.run(
                [*command, *arguments],
                cwd=working_directory,
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=30,
            )
            assert result.returncode == expected, (arguments, result.returncode, result.stderr)
            if expected:
                assert not result.stdout and result.stderr
            return result.stdout

        assert "PortWatch" in run("--version")
        assert "dashboard" in run("--help")
        run("inspect", "0", "--json", expected=2)
        fixture_code = (
            "import socket,time,os; s=socket.socket(); s.bind(('127.0.0.1',0)); "
            "s.listen(); print(s.getsockname()[1],flush=True); time.sleep(90)"
        )
        fixture = subprocess.Popen(
            [sys.executable, "-u", "-c", fixture_code],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=working_directory,
        )
        dashboard = None
        try:
            assert fixture.stdout is not None
            port = int(fixture.stdout.readline())
            listed = json.loads(run("list", "--json"))
            assert any(item["port"] == port and item["pid"] == fixture.pid for item in listed)
            inspected = json.loads(run("inspect", str(port), "--json"))
            assert inspected["pid"] == fixture.pid
            assert int(run("next", str(port))) > port
            with socket.socket() as reservation:
                reservation.bind(("127.0.0.1", 0))
                dashboard_port = reservation.getsockname()[1]
            base = f"http://127.0.0.1:{dashboard_port}"
            with Path(working_directory, "dashboard.log").open("w", encoding="utf-8") as log:
                dashboard = subprocess.Popen(
                    [*command, "dashboard", "--no-browser", "--port", str(dashboard_port)],
                    cwd=working_directory,
                    stdout=log,
                    stderr=log,
                    text=True,
                )
                deadline = time.monotonic() + 30
                while True:
                    try:
                        with urlopen(f"{base}/api/session", timeout=2) as response:
                            token = json.load(response)["token"]
                        break
                    except (URLError, TimeoutError):
                        assert dashboard.poll() is None, "Dashboard exited before serving HTTP"
                        if time.monotonic() >= deadline:
                            raise AssertionError("Dashboard startup timed out") from None
                        time.sleep(0.1)
                with urlopen(base, timeout=5) as response:
                    html = response.read().decode("utf-8")
                paths = set(re.findall(r'(?:href|src)="(/?[^"#]+\.(?:js|css|svg))"', html))
                paths.update({"dashboard-api.js", "dashboard-view.js", "dashboard-render.js"})
                assert paths
                for path in paths:
                    with urlopen(f"{base}/{path.lstrip('/')}", timeout=5) as response:
                        assert response.read(), path
                        if path.endswith(".js"):
                            assert response.headers.get_content_type() == "text/javascript"
                with urlopen(f"{base}/api/ports?start={port}&end={port}", timeout=10) as response:
                    assert json.load(response)["ports"][0]["pid"] == fixture.pid
                denied = Request(f"{base}/api/ports/{port}/terminate", data=b"{}")
                try:
                    urlopen(denied, timeout=5)
                except HTTPError as error:
                    assert error.code == 403
                else:
                    raise AssertionError("Dashboard accepted an unauthenticated action")
                action = Request(
                    f"{base}/api/ports/{port}/terminate",
                    data=json.dumps({"pid": fixture.pid}).encode(),
                    headers={
                        "Origin": base,
                        "Content-Type": "application/json",
                        "X-PortWatch-Token": token,
                    },
                )
                with urlopen(action, timeout=10) as response:
                    assert response.status == 200
                fixture.wait(timeout=5)
                run("inspect", str(port), "--json", expected=3)
        finally:
            if dashboard is not None:
                stop_child(dashboard)
            stop_child(fixture)
    print("Runtime smoke passed: CLI, live listeners, HTTP assets and confirmed termination.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--executable", type=Path)
    arguments = parser.parse_args()
    launch = (
        [str(arguments.executable.resolve())]
        if arguments.executable
        else [sys.executable, "-m", "portwatch"]
    )
    # No shell and no browser are launched by this check.
    verify_runtime(launch)
