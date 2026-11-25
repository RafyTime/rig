"""Set up a device's chezmoi checkout of a Rig configuration repository."""

import hashlib
import json
import os
import platform
import re
import sys
import urllib.request
from pathlib import Path

from rig import chezmoi

DEFAULT_REPO = "RafyTime/rig"
CHEZMOI_VERSION = "2.74.2"
INSTALL_HELP = (
    "install chezmoi from https://www.chezmoi.io/install/ and run rig init again"
)


class SetupError(Exception):
    """This device cannot be set up as requested."""


def is_configured(repo: str) -> bool:
    """Whether chezmoi already has a checkout of `repo`.

    Raises SetupError if the existing checkout belongs to another repository.
    """
    executable = chezmoi.find("init", "chezmoi")
    config = chezmoi_output(executable, "dump-config", "--format", "json")
    try:
        tree = Path(json.loads(config)["workingTree"])
    except (json.JSONDecodeError, KeyError, TypeError) as error:
        raise chezmoi.DependencyError(
            f"rig init could not read chezmoi's configuration ({error!r}). "
            "Check that `chezmoi doctor` passes, then try again."
        ) from error
    if not (tree / ".git").exists():
        return False
    origin = chezmoi_output(
        executable, "git", "--", "remote", "get-url", "origin"
    ).strip()
    if canonical(origin) != canonical(repo):
        raise SetupError(
            f"chezmoi already manages {tree}, a checkout of {origin}, not {repo}. "
            f"Run `rig init {origin}` to keep it, or move {tree} aside to set up "
            f"{repo} instead."
        )
    return True


def canonical(repo: str) -> str:
    """Reduce the ways to name a Git remote to one comparable form."""
    if re.fullmatch(r"[\w.-]+/[\w.-]+", repo):
        repo = f"github.com/{repo}"  # chezmoi's OWNER/NAME shorthand.
    repo = re.sub(r"^[a-z+]+://", "", repo)
    repo = re.sub(r"^[^@/]+@", "", repo)
    repo = repo.replace(":", "/", 1)  # scp-like `host:path`.
    return repo.removesuffix("/").removesuffix(".git").lower()


def chezmoi_output(executable: str, *args: str) -> str:
    """Capture what `chezmoi <args>` prints, raising SetupError if it fails."""
    result = chezmoi.launch("init", "chezmoi", [executable, *args], capture=True)
    if result.returncode != 0:
        raise SetupError(f"`chezmoi {' '.join(args)}` failed: {result.stderr.strip()}")
    return result.stdout


def install_chezmoi() -> Path:
    """Install the official chezmoi release where `chezmoi.find` looks for it.

    The binary is written only after it matches the release's published checksum.
    """
    asset = release_asset()
    # A test and mirror hook for serving the same release layout elsewhere; not a
    # documented user setting.
    releases = os.environ.get(
        "RIG_CHEZMOI_RELEASES_URL",
        "https://github.com/twpayne/chezmoi/releases/download",
    )
    base = f"{releases}/v{CHEZMOI_VERSION}"
    checksums = download(f"{base}/chezmoi_{CHEZMOI_VERSION}_checksums.txt").decode()
    binary = download(f"{base}/{asset}")
    expected = next(
        (
            fields[0]
            for line in checksums.splitlines()
            if (fields := line.split())[1:] == [asset]
        ),
        None,
    )
    if expected is None:
        raise SetupError(
            f"The chezmoi {CHEZMOI_VERSION} release publishes no checksum for "
            f"{asset}, so rig did not install it. To continue, {INSTALL_HELP}."
        )
    if hashlib.sha256(binary).hexdigest() != expected:
        raise SetupError(
            f"The downloaded {asset} does not match the checksum published with "
            f"chezmoi {CHEZMOI_VERSION}, so rig did not install it. To continue, {INSTALL_HELP}."
        )
    destination = chezmoi.local_bin() / (
        "chezmoi.exe" if sys.platform == "win32" else "chezmoi"
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_name(f".{destination.name}.download")
    partial.write_bytes(binary)
    partial.chmod(0o755)
    partial.replace(destination)
    return destination


def release_asset() -> str:
    if platform.machine().lower() in ("x86_64", "amd64"):
        if sys.platform == "linux":
            return "chezmoi-linux-amd64"
        if sys.platform == "win32":
            return "chezmoi-windows-amd64.exe"
    raise SetupError(
        f"rig init installs chezmoi only on x86-64 Linux and Windows. To continue, {INSTALL_HELP}."
    )


def download(url: str) -> bytes:
    try:
        with urllib.request.urlopen(url, timeout=60) as response:
            return response.read()
    except OSError as error:
        raise SetupError(
            f"rig init could not download chezmoi from {url}: {error}. "
            f"Check your connection, or {INSTALL_HELP}."
        ) from error
