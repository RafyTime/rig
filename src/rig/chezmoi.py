"""Delegate dotfile operations to the active chezmoi setup."""

import shutil
import subprocess
from pathlib import Path
from typing import Literal

type Tool = Literal["chezmoi", "uv"]

PURPOSE: dict[Tool, tuple[str, str]] = {
    "chezmoi": ("to manage dotfiles", "https://www.chezmoi.io/install/"),
    "uv": (
        "to run the skills engine",
        "https://docs.astral.sh/uv/getting-started/installation/",
    ),
}


class DependencyError(Exception):
    """A tool rig delegates to is missing or cannot be started."""


def local_bin() -> Path:
    """Where `rig init` installs chezmoi, which may not be on PATH."""
    return Path.home() / ".local" / "bin"


def find(command: str, tool: Tool) -> str:
    executable = shutil.which(tool)
    if executable is None and tool == "chezmoi":
        executable = shutil.which(tool, path=str(local_bin()))
    if executable is None:
        purpose, install = PURPOSE[tool]
        raise DependencyError(
            f"rig {command} needs {tool} {purpose}, but it is not on PATH. "
            f"Install it from {install} and try again."
        )
    return executable


def launch(
    command: str,
    tool: Tool,
    argv: list[str],
    *,
    capture: bool = False,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run a tool `find` located, reporting a failed start as a DependencyError."""
    try:
        return subprocess.run(
            argv, capture_output=capture, encoding="utf-8", env=env, check=False
        )
    except OSError as error:
        raise DependencyError(
            f"rig {command} could not start {tool} at {argv[0]}: {error}. "
            f"Reinstall it from {PURPOSE[tool][1]} and try again."
        ) from error


def exit_code(
    command: str, tool: Tool, argv: list[str], *, env: dict[str, str] | None = None
) -> int:
    """Run a tool with inherited stdio and return its exit code as a shell would."""
    try:
        code = launch(command, tool, argv, env=env).returncode
    except KeyboardInterrupt:
        return 130  # Shell convention for an interrupted command.
    # POSIX reports a signal death as -signum; shells report 128 + signum.
    return 128 - code if code < 0 else code


def run(command: str, *args: str, needs: tuple[Tool, ...] = ()) -> int:
    """Run `chezmoi <command>` with inherited stdio.

    Chezmoi resolves its own configured source and destination, so this works from
    any directory, and its output, prompts, and exit code reach the caller unchanged.
    """
    executable = find(command, "chezmoi")
    for tool in needs:
        find(command, tool)
    return exit_code(command, "chezmoi", [executable, command, *args])
