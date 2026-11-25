"""Command parsing and dispatch for the rig CLI."""

from importlib.metadata import version
from typing import Annotated

import typer
from rich.console import Console
from rich.text import Text

from rig import chezmoi, skills

# Rich drops styling when stderr is redirected, keeping scripted output plain.
errors = Console(stderr=True, highlight=False, soft_wrap=True)

app = typer.Typer(
    help="Manage your Rig setup across devices.",
    no_args_is_help=True,
    add_completion=False,
)
app.add_typer(skills.app, name="skills")


def show_version(value: bool) -> None:
    if value:
        typer.echo(f"rig {version('rig')}")
        raise typer.Exit()


@app.callback()
def root(
    _version: Annotated[
        bool,
        typer.Option(
            "--version",
            callback=show_version,
            is_eager=True,
            help="Show the installed rig version and exit.",
        ),
    ] = False,
) -> None:
    pass


def delegate(
    command: str, args: list[str], needs: tuple[chezmoi.Tool, ...] = ()
) -> None:
    try:
        code = chezmoi.run(command, *args, needs=needs)
    except chezmoi.DependencyError as error:
        errors.print(Text.assemble(("Error: ", "bold red"), str(error)))
        raise typer.Exit(1) from None
    raise typer.Exit(code)


# Extra arguments pass through to chezmoi, e.g. `rig diff --exclude scripts`.
PASSTHROUGH = {"allow_extra_args": True, "ignore_unknown_options": True}


@app.command(context_settings=PASSTHROUGH)
def diff(context: typer.Context) -> None:
    """Preview pending dotfile changes without writing anything."""
    delegate("diff", context.args)


@app.command(context_settings=PASSTHROUGH)
def apply(context: typer.Context) -> None:
    """Apply dotfiles, then sync skills once through the chezmoi hook."""
    delegate("apply", context.args, needs=("uv",))
