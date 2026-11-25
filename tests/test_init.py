"""Set up a device through `rig init` with substituted chezmoi and releases."""

import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from test_cli import rig

# Answers `dump-config` and `git` from an optional existing checkout and logs
# every call, so tests can observe what rig asked chezmoi to do.
FAKE_CHEZMOI = """\
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

with open(os.environ["FAKE_CHEZMOI_LOG"], "a") as log:
    print(json.dumps(sys.argv[1:]), file=log)
tree = os.environ["FAKE_WORKING_TREE"]
if sys.argv[1] == "dump-config":
    print(json.dumps({"sourceDir": tree, "workingTree": tree}))
elif sys.argv[1] == "git":
    print(Path(tree, ".git", "origin").read_text())
"""


def fake_chezmoi(directory: Path, name: str = "chezmoi") -> None:
    script = directory / "fake_chezmoi.py"
    script.write_text(FAKE_CHEZMOI)
    if os.name == "nt":
        launcher = f'@"{sys.executable}" "{script}" %*\n'
        (directory / f"{name}.cmd").write_text(launcher)
    else:
        launcher = directory / name
        launcher.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{script}" "$@"\n')
        launcher.chmod(0o755)


@pytest.fixture
def device(tmp_path: Path):
    """An isolated home with a fake chezmoi on PATH and no existing checkout."""
    tools, home = tmp_path / "bin", tmp_path / "home"
    tools.mkdir()
    home.mkdir()
    fake_chezmoi(tools)
    environment = dict(
        os.environ,
        PATH=str(tools),
        HOME=str(home),
        USERPROFILE=str(home),
        FAKE_CHEZMOI_LOG=str(tmp_path / "chezmoi.log"),
        FAKE_WORKING_TREE=str(home / ".local/share/chezmoi"),
    )
    return environment


def chezmoi_calls(environment: dict[str, str]) -> list[list[str]]:
    log = Path(environment["FAKE_CHEZMOI_LOG"])
    return [json.loads(line) for line in log.read_text().splitlines()]


def test_init_clones_rig_by_default_and_leaves_apply_to_the_user(
    device: dict[str, str],
):
    result = rig("init", env=device)

    assert result.returncode == 0, result.stderr
    assert ["init", "RafyTime/rig"] in chezmoi_calls(device)
    assert not any(call[0] == "apply" for call in chezmoi_calls(device))
    assert "rig diff" in result.stdout and "rig apply" in result.stdout


def existing_checkout(environment: dict[str, str], origin: str) -> None:
    git = Path(environment["FAKE_WORKING_TREE"], ".git")
    git.mkdir(parents=True)
    (git / "origin").write_text(origin)


@pytest.mark.parametrize(
    ("requested", "origin"),
    [
        ("RafyTime/rig", "https://github.com/RafyTime/rig.git"),
        ("rafytime/rig", "git@github.com:RafyTime/rig.git"),
        ("https://github.com/RafyTime/rig", "https://github.com/RafyTime/rig.git"),
    ],
)
def test_repeated_init_recognizes_the_configured_repository(
    device: dict[str, str], requested: str, origin: str
):
    existing_checkout(device, origin)

    result = rig("init", requested, env=device)

    assert result.returncode == 0, result.stderr
    assert not any(call[0] == "init" for call in chezmoi_calls(device))
    assert "already set up" in result.stdout


def test_init_stops_when_chezmoi_manages_another_repository(device: dict[str, str]):
    existing_checkout(device, "https://github.com/someone/dotfiles.git")

    result = rig("init", env=device)

    assert result.returncode == 1
    assert not any(call[0] == "init" for call in chezmoi_calls(device))
    assert "https://github.com/someone/dotfiles.git" in result.stderr
    assert "RafyTime/rig" in result.stderr
    assert "\x1b[" not in result.stderr


ASSET = "chezmoi-windows-amd64.exe" if os.name == "nt" else "chezmoi-linux-amd64"
INSTALLED = Path(".local/bin", "chezmoi.exe" if os.name == "nt" else "chezmoi")


def release(directory: Path, binary: bytes, checksum: str | None = None) -> str:
    """Serve a chezmoi release with its checksums file from a local directory."""
    from rig.setup import CHEZMOI_VERSION

    tag = directory / f"v{CHEZMOI_VERSION}"
    tag.mkdir(parents=True)
    (tag / ASSET).write_bytes(binary)
    checksum = checksum or hashlib.sha256(binary).hexdigest()
    other = "0" * 64
    (tag / f"chezmoi_{CHEZMOI_VERSION}_checksums.txt").write_text(
        f"{other}  chezmoi-darwin-arm64\n{checksum}  {ASSET}\n"
    )
    return directory.as_uri()


@pytest.fixture
def bare_device(tmp_path: Path):
    """An isolated home without chezmoi anywhere rig looks for it."""
    home = tmp_path / "home"
    home.mkdir()
    return dict(
        os.environ, PATH=str(tmp_path / "empty"), HOME=str(home), USERPROFILE=str(home)
    )


def test_init_refuses_a_chezmoi_download_with_a_wrong_checksum(
    tmp_path: Path, bare_device: dict[str, str]
):
    releases = release(tmp_path / "releases", b"tampered", checksum="f" * 64)

    result = rig("init", env=dict(bare_device, RIG_CHEZMOI_RELEASES_URL=releases))

    assert result.returncode == 1
    assert "checksum" in result.stderr
    assert "https://www.chezmoi.io/install/" in result.stderr
    assert not (Path(bare_device["HOME"]) / INSTALLED).exists()
    assert "Traceback" not in result.stderr


def test_init_without_chezmoi_or_its_release_explains_how_to_recover(
    tmp_path: Path, bare_device: dict[str, str]
):
    missing = (tmp_path / "offline").as_uri()

    result = rig("init", env=dict(bare_device, RIG_CHEZMOI_RELEASES_URL=missing))

    assert result.returncode == 1
    assert "could not download chezmoi" in result.stderr
    assert "https://www.chezmoi.io/install/" in result.stderr
    assert "Traceback" not in result.stderr


REPO = Path(__file__).parents[1]
RECORDING_SKILLS_ENGINE = """\
import sys
from pathlib import Path

with Path(__file__).with_name("sync-calls.log").open("a") as log:
    print(sys.argv[1:], file=log)
"""


# CI provisions all three, so a missing one fails there instead of skipping.
@pytest.mark.skipif(
    not (
        os.environ.get("CI")
        or all(shutil.which(tool) for tool in ("chezmoi", "git", "uv"))
    ),
    reason="chezmoi, git, and uv required",
)
def test_fresh_device_installs_chezmoi_then_previews_before_applying(tmp_path: Path):
    """Run the documented init, diff, apply sequence against real tools."""
    real_chezmoi = shutil.which("chezmoi")
    assert real_chezmoi
    # Serve the installed official binary as the release, so nothing downloads.
    releases = release(tmp_path / "releases", Path(real_chezmoi).read_bytes())
    path = os.pathsep.join(
        entry
        for entry in os.environ["PATH"].split(os.pathsep)
        if not shutil.which("chezmoi", path=entry)
    )
    if not (shutil.which("git", path=path) and shutil.which("uv", path=path)):
        pytest.skip("git or uv shares a directory with chezmoi")

    source = tmp_path / "config repo"
    (source / "agents").mkdir(parents=True)
    (source / ".chezmoiroot").write_text("home\n")
    shutil.copytree(REPO / "home/.chezmoiscripts", source / "home/.chezmoiscripts")
    (source / "agents/skills.py").write_text(RECORDING_SKILLS_ENGINE)
    (source / "home/dot_example").write_text("configuration")
    git = ["git", "-c", "user.name=Rig Test", "-c", "user.email=rig@example.invalid"]
    for command in (
        ["init", "--quiet"],
        ["add", "."],
        ["commit", "--quiet", "-m", "Rig"],
    ):
        subprocess.run([*git, *command], cwd=source, check=True, capture_output=True)

    home, elsewhere = tmp_path / "home", tmp_path / "cwd"
    home.mkdir()
    elsewhere.mkdir()
    environment = {
        key: value for key, value in os.environ.items() if not key.startswith("XDG_")
    }
    environment.update(
        PATH=path,
        HOME=str(home),
        USERPROFILE=str(home),
        UV_CACHE_DIR=str(tmp_path / "uv"),
        RIG_CHEZMOI_RELEASES_URL=releases,
    )
    repo = source.as_uri()

    initialized = rig("init", repo, cwd=elsewhere, env=environment)

    assert initialized.returncode == 0, initialized.stdout + initialized.stderr
    assert (home / INSTALLED).is_file()
    assert not (home / ".example").exists()

    again = rig("init", repo, cwd=elsewhere, env=environment)

    assert again.returncode == 0, again.stdout + again.stderr
    assert "already set up" in again.stdout

    preview = rig("diff", cwd=elsewhere, env=environment)

    assert preview.returncode == 0, preview.stdout + preview.stderr
    assert "configuration" in preview.stdout
    assert not (home / ".example").exists()

    applied = rig("apply", cwd=elsewhere, env=environment)

    assert applied.returncode == 0, applied.stdout + applied.stderr
    assert (home / ".example").read_text() == "configuration"
    sync_calls = home / ".local/share/chezmoi/agents/sync-calls.log"
    assert len(sync_calls.read_text().splitlines()) == 1
