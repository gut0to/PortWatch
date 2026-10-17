import json
import math
import time
import webbrowser
from collections.abc import Callable
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Annotated, NoReturn

import typer
from rich.console import Console
from rich.live import Live
from rich.text import Text

from portwatch.domain.exceptions import (
    InvalidPortError,
    PortNotFoundError,
    ProcessTerminationError,
)
from portwatch.domain.models import PortInfo
from portwatch.presentation.console import format_port_count, print_inspection
from portwatch.presentation.errors import report_system_errors
from portwatch.presentation.serializers import (
    port_to_dict,
    ports_to_csv,
    ports_to_json,
    ports_to_json_lines,
)
from portwatch.presentation.tables import ports_table, watch_view
from portwatch.services.monitoring import watch_snapshots
from portwatch.services.port_filters import filter_ports
from portwatch.services.port_service import PortService
from portwatch.services.reports import group_ports, summarize_ports
from portwatch.services.snapshots import (
    diff_snapshots,
    load_snapshot,
    redact_snapshot,
    write_snapshot,
)
from portwatch.system.termination import ProcessTerminator
from portwatch.utils.ports import parse_port_range, parse_port_selection, validate_port
from portwatch.web.server import create_server


class GroupField(StrEnum):
    none = "none"
    process = "process"
    project = "project"


class SortField(StrEnum):
    port = "port"
    pid = "pid"
    process = "process"
    project = "project"


app = typer.Typer(
    name="portwatch",
    help="Find out what's using your ports.",
    no_args_is_help=False,
)
console = Console()
service = PortService()
terminator = ProcessTerminator()


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: Annotated[bool, typer.Option("--version", help="Show the version.")] = False,
) -> None:
    if version:
        from portwatch import __version__

        typer.echo(f"PortWatch {__version__}")
        raise typer.Exit()
    elif ctx.invoked_subcommand is None:
        list_ports()


@app.command("list")
@report_system_errors
def list_ports(
    redact: Annotated[
        bool, typer.Option("--redact", help="Remove commands and working directories.")
    ] = False,
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write a UTF-8 snapshot file.")
    ] = None,
    overwrite: Annotated[
        bool, typer.Option("--overwrite", help="Replace an existing output file.")
    ] = False,
    json_lines: Annotated[
        bool, typer.Option("--json-lines", help="One JSON listener per line.")
    ] = False,
    count_only: Annotated[
        bool, typer.Option("--count", help="Print the matching listener count.")
    ] = False,
    quiet: Annotated[
        bool, typer.Option("--quiet", "-q", help="Print unique matching port numbers.")
    ] = False,
    offset: Annotated[
        int, typer.Option("--offset", min=0, help="Skip sorted results before limiting.")
    ] = 0,
    limit: Annotated[
        int, typer.Option("--limit", min=0, help="Maximum results; 0 returns all.")
    ] = 0,
    exact: Annotated[
        bool, typer.Option("--exact", help="Match process and project names exactly.")
    ] = False,
    exclude: Annotated[
        str | None, typer.Option("--exclude", help="Ports and ranges to exclude.")
    ] = None,
    selected_ports: Annotated[
        str | None, typer.Option("--ports", help="Ports and ranges, e.g. 80,3000-3010.")
    ] = None,
    as_csv: Annotated[bool, typer.Option("--csv", help="Print a CSV snapshot.")] = False,
    descending: Annotated[
        bool, typer.Option("--descending", help="Reverse the sort order.")
    ] = False,
    sort: Annotated[
        SortField, typer.Option("--sort", help="Sort results by a field.")
    ] = SortField.port,
    pid: Annotated[int | None, typer.Option("--pid", min=1, help="Filter by process ID.")] = None,
    process: Annotated[str, typer.Option("--process", help="Filter process names.")] = "",
    project: Annotated[str, typer.Option("--project", help="Filter detected project names.")] = "",
    search: Annotated[str, typer.Option("--search", help="Search listener metadata.")] = "",
    port_range: Annotated[
        str | None, typer.Option("--range", help="Filter ports, e.g. 3000-9000.")
    ] = None,
    as_json: Annotated[bool, typer.Option("--json", help="Print machine-readable JSON.")] = False,
) -> None:
    if overwrite and output is None:
        _fail("--overwrite requires --output.", 2)
    if output is not None and (quiet or count_only):
        _fail("--output requires JSON, JSON Lines, or CSV output.", 2)
    if sum((as_csv, as_json, quiet, count_only, json_lines)) > 1:
        _fail("Choose only one output format: --json, --csv, --quiet, --count, or --json-lines.", 2)
    try:
        excluded = parse_port_selection(exclude) if exclude is not None else frozenset()
        selection = parse_port_selection(selected_ports) if selected_ports is not None else None
        parsed_range = parse_port_range(port_range) if port_range else None
        ports = filter_ports(
            service.list_ports(parsed_range),
            search,
            pid=pid,
            process=process,
            project=project,
            exact=exact,
        )
    except InvalidPortError as error:
        _fail(str(error), 2)
    if selection is not None:
        ports = [item for item in ports if item.port in selection]
    ports = [item for item in ports if item.port not in excluded]
    keys: dict[SortField, Callable[[PortInfo], int | str]] = {
        SortField.port: lambda item: item.port,
        SortField.pid: lambda item: item.pid or 0,
        SortField.process: lambda item: (item.process_name or "").casefold(),
        SortField.project: lambda item: (item.project_name or "").casefold(),
    }
    ports = sorted(ports, key=keys[sort], reverse=descending)
    if redact:
        ports = redact_snapshot(ports)
    ports = ports[offset:]
    if limit:
        ports = ports[:limit]
    if output is not None:
        content = (
            ports_to_csv(ports)
            if as_csv
            else (ports_to_json_lines(ports) if json_lines else ports_to_json(ports))
        )
        try:
            write_snapshot(output, content, overwrite=overwrite)
        except FileExistsError:
            _fail("The output file already exists. Use --overwrite to replace it.", 2)
        return
    if json_lines:
        if ports:
            typer.echo(ports_to_json_lines(ports))
    elif count_only:
        typer.echo(str(len(ports)))
    elif quiet:
        for port_number in dict.fromkeys(item.port for item in ports):
            typer.echo(str(port_number))
    elif as_csv:
        typer.echo(ports_to_csv(ports))
    elif as_json:
        typer.echo(ports_to_json(ports))
    else:
        if ports:
            console.print(ports_table(ports))
        else:
            console.print("[dim]No listening TCP ports found.[/dim]")
        console.print(f"\n{format_port_count(len(ports))}")


@app.command()
@report_system_errors
def inspect(
    port: Annotated[int, typer.Argument(help="Port to inspect.")],
    as_json: Annotated[bool, typer.Option("--json", help="Print machine-readable JSON.")] = False,
) -> None:
    try:
        item = service.inspect(port)
    except (InvalidPortError, PortNotFoundError) as error:
        if isinstance(error, PortNotFoundError):
            _fail(str(error), 3)
        _fail(str(error), 2)
    if as_json:
        typer.echo(json.dumps(port_to_dict(item), indent=2))
    else:
        print_inspection(console, item)


@app.command()
@report_system_errors
def next(
    port: Annotated[int, typer.Argument(help="Starting port.")],
    as_json: Annotated[bool, typer.Option("--json", help="Print machine-readable JSON.")] = False,
    count: Annotated[
        int, typer.Option("--count", min=1, max=65535, help="Number of free ports needed.")
    ] = 1,
    end: Annotated[
        int, typer.Option("--end", min=1, max=65535, help="Last port to consider.")
    ] = 65535,
    verbose: Annotated[bool, typer.Option("--verbose", help="Explain the result.")] = False,
) -> None:
    if count > 1:
        try:
            found = service.available_ports(port, count, end)
        except InvalidPortError as error:
            _fail(str(error), 2)
        except PortNotFoundError as error:
            _fail(str(error), 3)
        if as_json:
            typer.echo(json.dumps({"start": port, "ports": found}))
        else:
            for candidate in found:
                typer.echo(f"Available port: {candidate}" if verbose else str(candidate))
        return
    try:
        available = (
            service.next_available(port) if end == 65535 else service.next_available(port, end)
        )
    except InvalidPortError as error:
        _fail(str(error), 2)
    except PortNotFoundError as error:
        _fail(str(error), 3)
    if as_json:
        typer.echo(json.dumps({"start": port, "port": available, "available": available == port}))
    elif verbose:
        console.print(f"Port {port} is {'available' if available == port else 'busy'}.")
        console.print(f"Next available port: {available}")
    else:
        typer.echo(str(available))


@app.command()
@report_system_errors
def kill(
    port: Annotated[int, typer.Argument(help="Port whose process should be terminated.")],
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip confirmation.")] = False,
    force: Annotated[
        bool, typer.Option("--force", help="Force termination if graceful exit fails.")
    ] = False,
) -> None:
    _terminate_port(port, yes=yes, force=force)


@app.command()
@report_system_errors
def free(
    port: Annotated[int, typer.Argument(help="Port to free.")],
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip confirmation.")] = False,
    force: Annotated[
        bool, typer.Option("--force", help="Force termination if graceful exit fails.")
    ] = False,
) -> None:
    _terminate_port(port, yes=yes, force=force, confirm_label="Kill process?")


@app.command()
@report_system_errors
def watch(
    search: Annotated[str, typer.Option("--search", help="Filter listener metadata.")] = "",
    pid: Annotated[int | None, typer.Option("--pid", min=1, help="Filter process IDs.")] = None,
    process: Annotated[str, typer.Option("--process", help="Filter process names.")] = "",
    project: Annotated[str, typer.Option("--project", help="Filter project names.")] = "",
    changes_only: Annotated[
        bool, typer.Option("--changes-only", help="Emit only changed snapshots.")
    ] = False,
    as_json: Annotated[
        bool, typer.Option("--json", help="Stream one JSON snapshot per scan.")
    ] = False,
    count: Annotated[
        int, typer.Option("--count", min=0, help="Stop after N scans; 0 watches forever.")
    ] = 0,
    interval: Annotated[
        float, typer.Option("--interval", min=0.2, help="Refresh interval in seconds.")
    ] = 2.0,
    port_range: Annotated[
        str | None, typer.Option("--range", help="Filter ports, e.g. 3000-9000.")
    ] = None,
) -> None:
    if not math.isfinite(interval):
        _fail("Refresh interval must be finite.", 2)
    try:
        parsed_range = parse_port_range(port_range) if port_range else None
    except InvalidPortError as error:
        _fail(str(error), 2)
    snapshots = watch_snapshots(
        lambda: filter_ports(
            service.list_ports(parsed_range), search, pid=pid, process=process, project=project
        ),
        interval,
        count,
        changes_only=changes_only,
        sleep=time.sleep,
    )
    try:
        if as_json:
            for ports in snapshots:
                typer.echo(
                    json.dumps(
                        {
                            "ports": [port_to_dict(item) for item in ports],
                            "scanned_at": datetime.now().astimezone().isoformat(),
                        }
                    )
                )
        else:
            with Live(console=console, refresh_per_second=max(1, int(1 / interval))) as live:
                for ports in snapshots:
                    live.update(watch_view(ports, interval))
    except KeyboardInterrupt:
        return


@app.command()
def dashboard(
    port: Annotated[
        int, typer.Option(min=0, max=65535, help="Local port to use; 0 selects an open port.")
    ] = 0,
    no_browser: Annotated[
        bool, typer.Option("--no-browser", help="Print the local URL without opening a browser.")
    ] = False,
) -> None:
    """Open the local browser dashboard."""
    if port:
        try:
            validate_port(port)
        except InvalidPortError as error:
            _fail(str(error), 2)

    try:
        server = create_server(service, terminator, port)
    except OSError as error:
        _fail(f"Could not start the local dashboard: {error}", 1)

    with server:
        console.print(f"PortWatch dashboard: [link={server.url}]{server.url}[/link]")
        if not no_browser:
            try:
                if not webbrowser.open_new_tab(server.url):
                    console.print("Open the local URL above in your browser.")
            except (OSError, webbrowser.Error):
                console.print("Open the local URL above in your browser.")
        try:
            server.serve_forever(poll_interval=0.5)
        except KeyboardInterrupt:
            console.print("Dashboard stopped.")


def _terminate_port(
    port: int, yes: bool, force: bool, confirm_label: str = "Kill this process?"
) -> None:
    try:
        item = service.inspect(port)
    except InvalidPortError as error:
        _fail(str(error), 2)
    except PortNotFoundError:
        typer.echo(f"Port {port} is available.")
        return
    console.print(Text(f"Port {port} is being used by:\n\nProcess: {item.process_name or '-'}"))
    console.print(Text(f"PID: {item.pid or '-'}\nProject: {item.project_name or '-'}\n"))
    if not yes and not typer.confirm(confirm_label, default=False):
        typer.echo("Operation cancelled.")
        return
    if item.pid is None:
        _fail("No process PID is available for this port.", 5)
    try:
        current = service.inspect(port)
    except PortNotFoundError:
        _fail("The listener changed during confirmation. Inspect the port again.", 5)
    if (current.pid, current.started_at) != (item.pid, item.started_at):
        _fail("The listener changed during confirmation. Inspect the port again.", 5)
    try:
        terminator.terminate(item.pid, force=force)
    except ProcessTerminationError as error:
        _fail(str(error), 5)
    typer.echo("Process terminated.")
    try:
        service.inspect(port)
    except PortNotFoundError:
        typer.echo(f"Port {port} is now available.")
        return
    _fail(f"Port {port} is still in use.", 5)


def _fail(message: str, code: int) -> NoReturn:
    typer.echo(message, err=True)
    raise typer.Exit(code=code)


@app.command()
@report_system_errors
def summary(
    group: Annotated[
        GroupField, typer.Option("--group", help="Group listener totals.")
    ] = GroupField.none,
    port_range: Annotated[str | None, typer.Option("--range", help="Inclusive port range.")] = None,
    search: Annotated[str, typer.Option("--search", help="Filter listener metadata.")] = "",
    as_json: Annotated[bool, typer.Option("--json", help="Print JSON totals.")] = False,
) -> None:
    """Summarize local TCP listeners without counting duplicate owners twice."""
    try:
        bounds = parse_port_range(port_range) if port_range else None
        ports = filter_ports(service.list_ports(bounds), search)
    except InvalidPortError as error:
        _fail(str(error), 2)
    totals = summarize_ports(ports)
    groups = (
        group_ports(ports, "project_name" if group == GroupField.project else "process_name")
        if group != GroupField.none
        else []
    )
    report: dict[str, object] = dict(totals)
    if group != GroupField.none:
        report["groups"] = groups
    if as_json:
        typer.echo(json.dumps(report))
    else:
        for label, value in totals.items():
            console.print(Text(f"{label.title()}: {value}"))
        for item in groups:
            console.print(Text(f"{item['name']}: {item['listeners']} listeners"))


@app.command("diff")
@report_system_errors
def compare_snapshots(
    before: Annotated[
        Path, typer.Argument(exists=True, dir_okay=False, help="Earlier JSON snapshot.")
    ],
    ignore: Annotated[
        list[str] | None,
        typer.Option("--ignore", help="Ignore a metadata field; repeat as needed."),
    ] = None,
    selected_ports: Annotated[
        str | None, typer.Option("--ports", help="Compare selected ports and ranges.")
    ] = None,
    search: Annotated[
        str, typer.Option("--search", help="Filter metadata in both snapshots.")
    ] = "",
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Save JSON differences.")
    ] = None,
    overwrite: Annotated[
        bool, typer.Option("--overwrite", help="Replace an existing report.")
    ] = False,
    after: Annotated[
        Path | None,
        typer.Argument(exists=True, dir_okay=False, help="Later snapshot; omit to scan now."),
    ] = None,
    exit_code: Annotated[
        bool, typer.Option("--exit-code", help="Exit 6 when snapshots differ.")
    ] = False,
    as_json: Annotated[
        bool, typer.Option("--json", help="Print added, removed, and changed listeners.")
    ] = False,
) -> None:
    """Compare saved snapshots or compare one snapshot with live listeners."""
    if overwrite and output is None:
        _fail("--overwrite requires --output.", 2)
    try:
        selection = parse_port_selection(selected_ports) if selected_ports is not None else None
        previous = load_snapshot(before)
        current = load_snapshot(after) if after else service.list_ports()
        if selection is not None:
            previous = [item for item in previous if item.port in selection]
            current = [item for item in current if item.port in selection]
        changes = diff_snapshots(
            filter_ports(previous, search),
            filter_ports(current, search),
            ignore_fields=frozenset(ignore or []),
        )
    except ValueError as error:
        _fail(f"Invalid snapshot: {error}", 2)
    if output is not None:
        try:
            write_snapshot(output, json.dumps(changes, indent=2), overwrite=overwrite)
        except FileExistsError:
            _fail("The output file exists. Use --overwrite to replace it.", 2)
    elif as_json:
        typer.echo(json.dumps(changes, indent=2))
    else:
        for kind, rows in changes.items():
            console.print(Text(f"{kind.title()}: {len(rows)}"))
            for row in rows:
                console.print(Text(json.dumps(row, ensure_ascii=False)))
    if exit_code and any(changes.values()):
        raise typer.Exit(code=6)
