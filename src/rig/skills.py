"""Run the active checkout's skills engine, as the chezmoi after-hook does."""

import json
import os
from pathlib import Path
from typing import Annotated

import typer

from rig import chezmoi
from rig.report import fail

app = typer.Typer(
    help="Sync and update skills from the active Rig checkout.",
    no_args_is_help=True,
)

# Same values the hook template reads, so both resolve the same engine and home.
CHECKOUT_PATHS_TEMPLATE = (
    '{{ dict "workingTree" .chezmoi.workingTree "destDir" .chezmoi.destDir | toJson }}'
)
SET_UP = "Set up Rig with `rig init` and try again."


def run_engine(command: str, *flags: str) -> int:
    """Run `skills.py <command>` from chezmoi's working tree against its destination."""
    name = f"skills {command}"
    executable = chezmoi.find(name, "chezmoi")
    uv = chezmoi.find(name, "uv")
    resolved = chezmoi.launch(
        name,
        "chezmoi",
        [executable, "execute-template", CHECKOUT_PATHS_TEMPLATE],
        capture=True,
    )
    if resolved.returncode != 0:
        found = resolved.stderr.strip() or f"chezmoi exited {resolved.returncode}"
        raise chezmoi.DependencyError(
            f"rig {name} could not find the active Rig checkout ({found}). {SET_UP}"
        )
    try:
        paths = json.loads(resolved.stdout)
        tree, home = paths["workingTree"], paths["destDir"]
    except (json.JSONDecodeError, KeyError, TypeError) as error:
        raise chezmoi.DependencyError(
            f"rig {name} could not read the active Rig checkout's paths from chezmoi "
            f"({error!r}). Check that `chezmoi doctor` passes, then try again."
        ) from error
    engine = Path(tree, "agents", "skills.py")
    if not engine.is_file():
        raise chezmoi.DependencyError(
            f"rig {name} could not find the active Rig checkout "
            f"(no skills engine at {engine}). {SET_UP}"
        )
    # The engine prints emoji; keep them intact when output is redirected on Windows.
    environment = dict(os.environ, PYTHONIOENCODING="utf-8")
    argv = [uv, "run", "--script", str(engine), command, "--home", home, *flags]
    return chezmoi.exit_code(name, "uv", argv, env=environment)


def delegate_to_engine(command: str, flags: list[str]) -> None:
    try:
        code = run_engine(command, *flags)
    except chezmoi.DependencyError as error:
        fail(error)
    raise typer.Exit(code)


DryRun = Annotated[
    bool, typer.Option("--dry-run", help="Plan changes without downloads or writes.")
]


@app.command()
def sync(
    dry_run: DryRun = False,
    adopt_existing: Annotated[
        bool,
        typer.Option(
            "--adopt-existing",
            help="Adopt matching existing installs, or transfer ownership to an "
            "identical custom skill.",
        ),
    ] = False,
) -> None:
    """Install missing selections and refresh custom skills; keep downloaded versions."""
    flags = []
    if dry_run:
        flags.append("--dry-run")
    if adopt_existing:
        flags.append("--adopt-existing")
    delegate_to_engine("sync", flags)


@app.command()
def update(dry_run: DryRun = False) -> None:
    """Refresh selected downloaded skills from upstream."""
    delegate_to_engine("update", ["--dry-run"] if dry_run else [])
