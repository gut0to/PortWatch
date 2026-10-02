import json
import time
import webbrowser
from typing import Annotated, NoReturn

import typer
from rich.console import Console
from rich.live import Live

from portwatch.domain.exceptions import (
    InvalidPortError,
    PortNotFoundError,
    ProcessTerminationError,
)
from portwatch.presentation.console import format_port_count, print_inspection
from portwatch.presentation.serializers import port_to_dict, ports_to_json
from portwatch.presentation.tables import ports_table, watch_view
from portwatch.services.port_service import PortService
from portwatch.system.termination import ProcessTerminator
from portwatch.utils.ports import parse_port_range, validate_port
from portwatch.web.server import create_server

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
    elif ctx.invoked_subcommand is None:
        list_ports()


@app.command("list")
def list_ports(
    port_range: Annotated[
        str | None, typer.Option("--range", help="Filter ports, e.g. 3000-9000.")
    ] = None,
    as_json: Annotated[bool, typer.Option("--json", help="Print machine-readable JSON.")] = False,
) -> None:
    try:
        parsed_range = parse_port_range(port_range) if port_range else None
        ports = service.list_ports(parsed_range)
    except InvalidPortError as error:
        _fail(str(error), 2)
    if as_json:
        typer.echo(ports_to_json(ports))
    else:
        if ports:
            console.print(ports_table(ports))
        else:
            console.print("[dim]No listening TCP ports found.[/dim]")
        console.print(f"\n{format_port_count(len(ports))}")


@app.command()
def inspect(
    port: Annotated[int, typer.Argument(help="Port to inspect.")],
    as_json: Annotated[bool, typer.Option("--json", help="Print machine-readable JSON.")] = False,
) -> None:
    try:
        item = service.inspect(port)
    except (InvalidPortError, PortNotFoundError) as error:
        if isinstance(error, PortNotFoundError):
            typer.echo(str(error))
            raise typer.Exit(code=3) from error
        _fail(str(error), 2)
    if as_json:
        typer.echo(json.dumps(port_to_dict(item), indent=2))
    else:
        print_inspection(console, item)


@app.command()
def next(
    port: Annotated[int, typer.Argument(help="Starting port.")],
    verbose: Annotated[bool, typer.Option("--verbose", help="Explain the result.")] = False,
) -> None:
    try:
        available = service.next_available(port)
    except InvalidPortError as error:
        _fail(str(error), 2)
    if verbose:
        console.print(f"Port {port} is {'available' if available == port else 'busy'}.")
        console.print(f"Next available port: {available}")
    else:
        typer.echo(str(available))


@app.command()
def kill(
    port: Annotated[int, typer.Argument(help="Port whose process should be terminated.")],
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip confirmation.")] = False,
    force: Annotated[
        bool, typer.Option("--force", help="Force termination if graceful exit fails.")
    ] = False,
) -> None:
    _terminate_port(port, yes=yes, force=force)


@app.command()
def free(
    port: Annotated[int, typer.Argument(help="Port to free.")],
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip confirmation.")] = False,
    force: Annotated[
        bool, typer.Option("--force", help="Force termination if graceful exit fails.")
    ] = False,
) -> None:
    _terminate_port(port, yes=yes, force=force, confirm_label="Kill process?")


@app.command()
def watch(
    interval: Annotated[
        float, typer.Option("--interval", min=0.2, help="Refresh interval in seconds.")
    ] = 2.0,
    port_range: Annotated[
        str | None, typer.Option("--range", help="Filter ports, e.g. 3000-9000.")
    ] = None,
) -> None:
    try:
        parsed_range = parse_port_range(port_range) if port_range else None
    except InvalidPortError as error:
        _fail(str(error), 2)
    try:
        with Live(console=console, refresh_per_second=max(1, int(1 / interval))) as live:
            while True:
                ports = service.list_ports(parsed_range)
                live.update(watch_view(ports, interval))
                time.sleep(interval)
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
    console.print(f"Port {port} is being used by:\n\nProcess: {item.process_name or '-'}")
    console.print(f"PID: {item.pid or '-'}\nProject: {item.project_name or '-'}\n")
    if not yes and not typer.confirm(confirm_label, default=False):
        typer.echo("Operation cancelled.")
        return
    if item.pid is None:
        _fail("No process PID is available for this port.", 5)
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
    typer.echo(f"Port {port} is still in use.", err=True)


def _fail(message: str, code: int) -> NoReturn:
    typer.echo(message, err=True)
    raise typer.Exit(code=code)
