"""Command parsing and dispatch for the rig CLI."""

import shutil
from importlib.metadata import version
from typing import Annotated

import typer

from rig import bootstrap, chezmoi, skills
from rig.report import errors, fail

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
        fail(error)
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


@app.command(context_settings=PASSTHROUGH)
def update(
    context: typer.Context,
    no_apply: Annotated[
        bool,
        typer.Option(
            "--no-apply", help="Pull only; leave dotfiles and skills untouched."
        ),
    ] = False,
) -> None:
    """Pull Rig, then apply it and sync skills once through the chezmoi hook."""
    if no_apply:
        # Without apply, chezmoi runs no scripts, so the skill sync hook stays idle.
        delegate("update", ["--apply=false", *context.args])
    else:
        delegate("update", context.args, needs=("uv",))


@app.command()
def init(
    repo: Annotated[
        str,
        typer.Argument(help="Configuration repository: OWNER/NAME or a Git URL."),
    ] = bootstrap.DEFAULT_REPO,
) -> None:
    """Set up this device's Rig checkout without applying it."""
    try:
        try:
            chezmoi.find("init", "chezmoi")
        except chezmoi.DependencyError:
            with errors.status(f"Installing chezmoi {bootstrap.CHEZMOI_VERSION}..."):
                installed = bootstrap.install_chezmoi()
            errors.print(f"Installed verified chezmoi to {installed}.")
            if shutil.which("chezmoi") is None:
                errors.print(
                    f"Rig finds it there; add {installed.parent} to PATH "
                    "to run chezmoi directly."
                )
        if bootstrap.is_configured(repo):
            typer.echo(f"Rig is already set up from {repo}.")
            raise typer.Exit()
        code = chezmoi.run("init", repo)
    except (chezmoi.DependencyError, bootstrap.SetupError) as error:
        fail(error)
    if code == 0:
        typer.echo("Rig is set up. Run `rig diff` to preview, then `rig apply`.")
    raise typer.Exit(code)
