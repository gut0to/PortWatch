import json
import math
import platform
import time
import webbrowser
from collections.abc import Callable
from contextlib import ExitStack
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Annotated, NoReturn, cast

import psutil
import typer
from rich.console import Console
from rich.live import Live
from rich.text import Text

from portwatch.domain.exceptions import (
    InvalidPortError,
    PortNotFoundError,
    ProcessTerminationError,
)
from portwatch.domain.models import PortInfo, PortRange
from portwatch.presentation.console import format_port_count, print_inspection
from portwatch.presentation.errors import report_system_errors
from portwatch.presentation.serializers import (
    changes_to_csv,
    port_to_dict,
    ports_to_csv,
    ports_to_json,
    ports_to_json_lines,
)
from portwatch.presentation.tables import ports_table, watch_view
from portwatch.services.history import (
    SnapshotFrame,
    history_events,
    history_to_csv,
    load_history,
    parse_history_time,
    summarize_history,
)
from portwatch.services.monitoring import watch_snapshots
from portwatch.services.port_filters import filter_ports
from portwatch.services.port_service import PortService
from portwatch.services.reports import group_ports, summarize_ports
from portwatch.services.snapshots import (
    diff_snapshots,
    load_snapshot,
    redact_changes,
    redact_snapshot,
    write_snapshot,
)
from portwatch.system.termination import ProcessTerminator
from portwatch.utils.ports import parse_port_range, parse_port_selection, validate_port
from portwatch.web.server import create_server


class ExpectedPortState(StrEnum):
    free = "free"
    busy = "busy"


class SnapshotFormat(StrEnum):
    json = "json"
    jsonl = "jsonl"
    csv = "csv"


class GroupSortField(StrEnum):
    name = "name"
    listeners = "listeners"
    ports = "ports"
    processes = "processes"
    projects = "projects"


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
    input_path: Annotated[
        Path | None,
        typer.Option(
            "--input",
            exists=True,
            dir_okay=False,
            help="Read a saved snapshot instead of scanning.",
        ),
    ] = None,
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
            _read_ports(input_path, parsed_range),
            search,
            pid=pid,
            process=process,
            project=project,
            exact=exact,
        )
    except ValueError as error:
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
    input_path: Annotated[
        Path | None,
        typer.Option("--input", exists=True, dir_okay=False, help="Inspect a saved snapshot."),
    ] = None,
    all_owners: Annotated[
        bool, typer.Option("--all", help="Inspect every process owning this port.")
    ] = False,
    as_json: Annotated[bool, typer.Option("--json", help="Print machine-readable JSON.")] = False,
) -> None:
    try:
        if input_path is None:
            items = service.inspect_all(port) if all_owners else [service.inspect(port)]
        else:
            validate_port(port)
            items = _read_ports(input_path, PortRange(port, port))
            if not items:
                raise PortNotFoundError(f"Port {port} is absent from the snapshot.")
            if not all_owners:
                items = items[:1]
    except (ValueError, PortNotFoundError) as error:
        if isinstance(error, PortNotFoundError):
            _fail(str(error), 3)
        _fail(str(error), 2)
    if as_json:
        typer.echo(
            ports_to_json(items) if all_owners else json.dumps(port_to_dict(items[0]), indent=2)
        )
    else:
        for item in items:
            print_inspection(console, item)


@app.command()
@report_system_errors
def next(
    port: Annotated[int, typer.Argument(help="Starting port.")],
    contiguous: Annotated[
        bool, typer.Option("--contiguous", help="Require consecutive free port numbers.")
    ] = False,
    exclude: Annotated[
        str | None, typer.Option("--exclude", help="Skip reserved ports and ranges.")
    ] = None,
    as_json: Annotated[bool, typer.Option("--json", help="Print machine-readable JSON.")] = False,
    count: Annotated[
        int, typer.Option("--count", min=1, max=65535, help="Number of free ports needed.")
    ] = 1,
    end: Annotated[
        int, typer.Option("--end", min=1, max=65535, help="Last port to consider.")
    ] = 65535,
    verbose: Annotated[bool, typer.Option("--verbose", help="Explain the result.")] = False,
) -> None:
    try:
        excluded = parse_port_selection(exclude) if exclude is not None else frozenset()
    except InvalidPortError as error:
        _fail(str(error), 2)
    if count > 1 or excluded or contiguous:
        try:
            found = (
                service.available_port_block(port, count, end, excluded=excluded)
                if contiguous
                else service.available_ports(port, count, end, excluded=excluded)
            )
        except InvalidPortError as error:
            _fail(str(error), 2)
        except PortNotFoundError as error:
            _fail(str(error), 3)
        if as_json:
            typer.echo(
                json.dumps(
                    {"start": port, "ports": found}
                    if count > 1
                    else {"start": port, "port": found[0], "available": found[0] == port}
                )
            )
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
    duration: Annotated[
        float | None,
        typer.Option("--duration", min=0.2, help="Maximum monitoring duration in seconds."),
    ] = None,
    skip_initial: Annotated[
        bool, typer.Option("--skip-initial", help="Establish a baseline without emitting it.")
    ] = False,
    exact: Annotated[
        bool, typer.Option("--exact", help="Require exact process and project names.")
    ] = False,
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write a new UTF-8 JSON Lines watch log.")
    ] = None,
    redact: Annotated[
        bool, typer.Option("--redact", help="Hide commands and working directories.")
    ] = False,
    selected_ports: Annotated[
        str | None, typer.Option("--ports", help="Watch selected ports and ranges.")
    ] = None,
    exclude: Annotated[
        str | None, typer.Option("--exclude", help="Exclude ports and ranges.")
    ] = None,
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
    if duration is not None and not math.isfinite(duration):
        _fail("Watch duration must be finite.", 2)
    if not math.isfinite(interval):
        _fail("Refresh interval must be finite.", 2)
    try:
        selection = parse_port_selection(selected_ports) if selected_ports is not None else None
        excluded = parse_port_selection(exclude) if exclude is not None else frozenset()
        parsed_range = parse_port_range(port_range) if port_range else None
    except InvalidPortError as error:
        _fail(str(error), 2)

    def scan_selected() -> list[PortInfo]:
        ports = filter_ports(
            service.list_ports(parsed_range),
            search,
            pid=pid,
            process=process,
            project=project,
            exact=exact,
        )
        return [
            item
            for item in ports
            if (selection is None or item.port in selection) and item.port not in excluded
        ]

    snapshots = watch_snapshots(
        scan_selected,
        interval,
        count,
        duration=duration,
        changes_only=changes_only,
        skip_initial=skip_initial,
        sleep=time.sleep,
    )
    try:
        with ExitStack() as stack:
            try:
                stream = (
                    stack.enter_context(output.open("x", encoding="utf-8", newline="\n"))
                    if output is not None
                    else None
                )
            except FileExistsError:
                _fail("The watch log already exists. Choose a new output path.", 2)
            if as_json or stream is not None:
                for ports in snapshots:
                    payload = json.dumps(
                        {
                            "ports": [
                                port_to_dict(item)
                                for item in (redact_snapshot(ports) if redact else ports)
                            ],
                            "scanned_at": datetime.now().astimezone().isoformat(),
                        }
                    )
                    if stream is None:
                        typer.echo(payload)
                    else:
                        stream.write(payload + "\n")
                        stream.flush()
            else:
                with Live(console=console, refresh_per_second=max(1, int(1 / interval))) as live:
                    for ports in snapshots:
                        live.update(
                            watch_view(redact_snapshot(ports) if redact else ports, interval)
                        )
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
    input_path: Annotated[
        Path | None,
        typer.Option("--input", exists=True, dir_okay=False, help="Summarize a saved snapshot."),
    ] = None,
    sort: Annotated[
        GroupSortField, typer.Option("--sort", help="Order grouped summary rows.")
    ] = GroupSortField.name,
    descending: Annotated[
        bool, typer.Option("--descending", help="Reverse grouped row order.")
    ] = False,
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Save a JSON summary.")
    ] = None,
    overwrite: Annotated[
        bool, typer.Option("--overwrite", help="Replace an existing summary.")
    ] = False,
    process: Annotated[str, typer.Option("--process", help="Filter process names.")] = "",
    project: Annotated[str, typer.Option("--project", help="Filter project names.")] = "",
    exact: Annotated[
        bool, typer.Option("--exact", help="Require exact process and project names.")
    ] = False,
    pid: Annotated[int | None, typer.Option("--pid", min=1, help="Summarize a process ID.")] = None,
    selected_ports: Annotated[
        str | None, typer.Option("--ports", help="Select ports and ranges.")
    ] = None,
    exclude: Annotated[
        str | None, typer.Option("--exclude", help="Exclude ports and ranges.")
    ] = None,
    group: Annotated[
        GroupField, typer.Option("--group", help="Group listener totals.")
    ] = GroupField.none,
    port_range: Annotated[str | None, typer.Option("--range", help="Inclusive port range.")] = None,
    search: Annotated[str, typer.Option("--search", help="Filter listener metadata.")] = "",
    as_json: Annotated[bool, typer.Option("--json", help="Print JSON totals.")] = False,
) -> None:
    """Summarize local TCP listeners without counting duplicate owners twice."""
    if group == GroupField.none and (sort != GroupSortField.name or descending):
        _fail("Group sorting requires --group.", 2)
    if overwrite and output is None:
        _fail("--overwrite requires --output.", 2)
    try:
        selection = parse_port_selection(selected_ports) if selected_ports is not None else None
        excluded = parse_port_selection(exclude) if exclude is not None else frozenset()
        bounds = parse_port_range(port_range) if port_range else None
        ports = filter_ports(
            _read_ports(input_path, bounds),
            search,
            pid=pid,
            process=process,
            project=project,
            exact=exact,
        )
    except ValueError as error:
        _fail(str(error), 2)
    ports = [
        item
        for item in ports
        if (selection is None or item.port in selection) and item.port not in excluded
    ]
    totals = summarize_ports(ports)
    groups = (
        group_ports(ports, "project_name" if group == GroupField.project else "process_name")
        if group != GroupField.none
        else []
    )
    groups.sort(
        key=lambda row: (
            str(row["name"]).casefold()
            if sort == GroupSortField.name
            else cast(int, row[sort.value])
        ),
        reverse=descending,
    )
    report: dict[str, object] = dict(totals)
    if group != GroupField.none:
        report["groups"] = groups
    if output is not None:
        try:
            write_snapshot(output, json.dumps(report, indent=2), overwrite=overwrite)
        except FileExistsError:
            _fail("The output file exists. Use --overwrite to replace it.", 2)
    elif as_json:
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
    redact: Annotated[
        bool, typer.Option("--redact", help="Hide command lines and directories in reports.")
    ] = False,
    as_csv: Annotated[bool, typer.Option("--csv", help="Print CSV differences.")] = False,
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
    if as_csv and as_json:
        _fail("Choose either --json or --csv.", 2)
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
    if redact:
        changes = redact_changes(changes)
    if output is not None:
        try:
            write_snapshot(
                output,
                changes_to_csv(changes) if as_csv else json.dumps(changes, indent=2),
                overwrite=overwrite,
            )
        except FileExistsError:
            _fail("The output file exists. Use --overwrite to replace it.", 2)
    elif as_csv:
        typer.echo(changes_to_csv(changes))
    elif as_json:
        typer.echo(json.dumps(changes, indent=2))
    else:
        for kind, rows in changes.items():
            console.print(Text(f"{kind.title()}: {len(rows)}"))
            for row in rows:
                console.print(Text(json.dumps(row, ensure_ascii=False)))
    if exit_code and any(changes.values()):
        raise typer.Exit(code=6)


@app.command()
def doctor(
    as_json: Annotated[
        bool, typer.Option("--json", help="Print local diagnostic results as JSON.")
    ] = False,
) -> None:
    """Check the local runtime and TCP scanner without terminating processes."""
    from portwatch import __version__

    report: dict[str, object] = {
        "portwatch": __version__,
        "python": platform.python_version(),
        "platform": platform.system(),
        "architecture": platform.machine(),
        "psutil": psutil.__version__,
    }
    code = 0
    try:
        report["listeners"] = len(service.scanner.list_listening_ports())
        report["scan"] = "ok"
    except OSError as error:
        report["scan"] = "unavailable"
        report["error"] = str(error)
        code = 4 if isinstance(error, PermissionError) else 1
    if as_json:
        typer.echo(json.dumps(report))
    else:
        for label, value in report.items():
            console.print(Text(f"{label}: {value}"))
    if code:
        raise typer.Exit(code=code)


@app.command("history")
@report_system_errors
def history_report(
    path: Annotated[
        Path, typer.Argument(exists=True, dir_okay=False, help="JSON Lines watch log.")
    ],
    selected_ports: Annotated[
        str | None, typer.Option("--ports", help="Analyze selected ports.")
    ] = None,
    exclude: Annotated[
        str | None, typer.Option("--exclude", help="Exclude selected ports.")
    ] = None,
    search: Annotated[
        str, typer.Option("--search", help="Filter historical listener metadata.")
    ] = "",
    pid: Annotated[
        int | None, typer.Option("--pid", min=1, help="Filter historical process IDs.")
    ] = None,
    since: Annotated[
        str | None, typer.Option("--since", help="Inclusive ISO timestamp with timezone.")
    ] = None,
    until: Annotated[
        str | None, typer.Option("--until", help="Inclusive ISO timestamp with timezone.")
    ] = None,
    events: Annotated[
        bool, typer.Option("--events", help="Include timestamped listener transitions.")
    ] = False,
    as_csv: Annotated[
        bool, typer.Option("--csv", help="Print listener totals for every scan.")
    ] = False,
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Save a history report.")
    ] = None,
    overwrite: Annotated[
        bool, typer.Option("--overwrite", help="Replace an existing report.")
    ] = False,
    as_json: Annotated[bool, typer.Option("--json", help="Print history metrics as JSON.")] = False,
) -> None:
    """Analyze saved watch logs without scanning this machine."""
    if overwrite and output is None:
        _fail("--overwrite requires --output.", 2)
    if as_csv and (as_json or events):
        _fail("--csv cannot be combined with --json or --events.", 2)
    try:
        start_time = parse_history_time(since) if since else None
        end_time = parse_history_time(until) if until else None
        if start_time and end_time and start_time > end_time:
            raise ValueError("--since must not be after --until.")
        frames = [
            frame
            for frame in load_history(path)
            if (start_time is None or frame.scanned_at >= start_time)
            and (end_time is None or frame.scanned_at <= end_time)
        ]
        selection = parse_port_selection(selected_ports) if selected_ports is not None else None
        excluded = parse_port_selection(exclude) if exclude is not None else frozenset()
        frames = [
            SnapshotFrame(
                frame.scanned_at,
                tuple(
                    item
                    for item in frame.ports
                    if (selection is None or item.port in selection) and item.port not in excluded
                ),
            )
            for frame in frames
        ]
        frames = [
            SnapshotFrame(frame.scanned_at, tuple(filter_ports(list(frame.ports), search, pid=pid)))
            for frame in frames
        ]
        report: dict[str, object] = dict(summarize_history(frames))
        if events:
            report["events"] = history_events(frames)
    except ValueError as error:
        _fail(str(error), 2)
    if output is not None:
        try:
            write_snapshot(
                output,
                history_to_csv(frames) if as_csv else json.dumps(report, indent=2),
                overwrite=overwrite,
            )
        except FileExistsError:
            _fail("The report exists. Use --overwrite to replace it.", 2)
    elif as_csv:
        typer.echo(history_to_csv(frames))
    elif as_json:
        typer.echo(json.dumps(report))
    else:
        for label, value in report.items():
            console.print(Text(f"{label}: {value}"))


@app.command("convert")
@report_system_errors
def convert_snapshot(
    path: Annotated[
        Path, typer.Argument(exists=True, dir_okay=False, help="Listener snapshot file.")
    ],
    search: Annotated[
        str, typer.Option("--search", help="Filter listener metadata before conversion.")
    ] = "",
    selected_ports: Annotated[
        str | None, typer.Option("--ports", help="Select ports and ranges.")
    ] = None,
    redact: Annotated[
        bool, typer.Option("--redact", help="Remove commands and directories.")
    ] = False,
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Save the converted snapshot.")
    ] = None,
    overwrite: Annotated[
        bool, typer.Option("--overwrite", help="Replace an existing output file.")
    ] = False,
    to: Annotated[
        SnapshotFormat, typer.Option("--to", help="Target snapshot format.")
    ] = SnapshotFormat.json,
) -> None:
    """Convert validated snapshots between JSON, JSON Lines, and CSV."""
    if overwrite and output is None:
        _fail("--overwrite requires --output.", 2)
    try:
        selection = parse_port_selection(selected_ports) if selected_ports is not None else None
        ports = filter_ports(load_snapshot(path), search)
        if selection is not None:
            ports = [item for item in ports if item.port in selection]
        if redact:
            ports = redact_snapshot(ports)
    except ValueError as error:
        _fail(str(error), 2)
    content = (
        ports_to_csv(ports)
        if to == SnapshotFormat.csv
        else (ports_to_json_lines(ports) if to == SnapshotFormat.jsonl else ports_to_json(ports))
    )
    if output is not None:
        try:
            write_snapshot(output, content, overwrite=overwrite)
        except FileExistsError:
            _fail("The output file exists. Use --overwrite to replace it.", 2)
    elif content:
        typer.echo(content)


def _read_ports(input_path: Path | None, bounds: PortRange | None = None) -> list[PortInfo]:
    if input_path is None:
        return service.list_ports(bounds)
    ports = load_snapshot(input_path)
    return [item for item in ports if bounds is None or bounds.start <= item.port <= bounds.end]


@app.command("check")
@report_system_errors
def check_port(
    ports: Annotated[str, typer.Argument(help="Port whose listening state should be checked.")],
    expect: Annotated[
        ExpectedPortState, typer.Option("--expect", help="Expected listening state.")
    ] = ExpectedPortState.free,
    as_json: Annotated[
        bool, typer.Option("--json", help="Print the check result as JSON.")
    ] = False,
) -> None:
    """Check a port's scan state; exit 7 when it differs from the expectation."""
    try:
        selected = parse_port_selection(ports)
    except InvalidPortError as error:
        _fail(str(error), 2)
    occupied = {item.port for item in service.scanner.list_listening_ports()}
    results = [
        {
            "port": port,
            "listening": port in occupied,
            "expected": expect.value,
            "matches": (port in occupied) == (expect == ExpectedPortState.busy),
        }
        for port in sorted(selected)
    ]
    matches = all(item["matches"] for item in results)
    if as_json:
        typer.echo(
            json.dumps(results[0] if len(results) == 1 else {"ports": results, "matches": matches})
        )
    else:
        for item in results:
            console.print(Text(f"Port {item['port']}: {'busy' if item['listening'] else 'free'}"))
    if not matches:
        raise typer.Exit(code=7)
