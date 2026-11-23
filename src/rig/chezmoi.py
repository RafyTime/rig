"""Delegate dotfile operations to the active chezmoi setup."""

import shutil
import subprocess
from typing import Literal

type Tool = Literal["chezmoi", "uv"]

PURPOSE: dict[Tool, tuple[str, str]] = {
    "chezmoi": ("to manage dotfiles", "https://www.chezmoi.io/install/"),
    "uv": (
        "to run the skill sync hook",
        "https://docs.astral.sh/uv/getting-started/installation/",
    ),
}


class MissingDependency(Exception):
    def __init__(self, command: str, tool: Tool) -> None:
        purpose, install = PURPOSE[tool]
        super().__init__(
            f"rig {command} needs {tool} {purpose}, but it is not on PATH. "
            f"Install it from {install} and try again."
        )


def find(command: str, tool: Tool) -> str:
    executable = shutil.which(tool)
    if executable is None:
        raise MissingDependency(command, tool)
    return executable


def run(command: str, *args: str, needs: tuple[Tool, ...] = ()) -> int:
    """Run `chezmoi <command>` with inherited stdio.

    Chezmoi resolves its own configured source and destination, so this works from
    any directory, and its output, prompts, and exit code reach the caller unchanged.
    """
    executable = find(command, "chezmoi")
    for tool in needs:
        find(command, tool)
    try:
        return subprocess.run([executable, command, *args], check=False).returncode
    except KeyboardInterrupt:
        return 130
