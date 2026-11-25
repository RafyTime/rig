"""Pull Rig from a test repository and apply it with the real chezmoi and hook."""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from test_cli import REPO, needs_chezmoi_and_uv, rig

# Stands in for `bunx skills@latest add <source> --skill <names>...`: it stages
# the current upstream text for each requested skill and logs the download.
FAKE_DOWNLOAD = """\
import sys
from pathlib import Path

here = Path(__file__).parent
names = sys.argv[sys.argv.index("--skill") + 1 : sys.argv.index("--agent")]
for name in names:
    skill = Path(".agents/skills", name)
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text((here / "upstream.txt").read_text())
with (here / "downloads.log").open("a") as log:
    print(*names, file=log)
"""


def fake_bunx(directory: Path) -> None:
    script = directory / "fake_download.py"
    script.write_text(FAKE_DOWNLOAD)
    if os.name == "nt":
        (directory / "bunx.cmd").write_text(f'@"{sys.executable}" "{script}" %*\n')
    else:
        bunx = directory / "bunx"
        bunx.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{script}" "$@"\n')
        bunx.chmod(0o755)


def git(*args: str, cwd: Path) -> str:
    result = subprocess.run(
        ["git", "-c", "user.name=Rig Test", "-c", "user.email=rig@example.invalid"]
        + list(args),
        cwd=cwd,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return result.stdout.strip()


def publish(upstream: Path, configuration: str) -> str:
    (upstream / "home/dot_example").write_text(configuration)
    git("commit", "--quiet", "--all", "--message", configuration, cwd=upstream)
    return git("rev-parse", "HEAD", cwd=upstream)


@needs_chezmoi_and_uv
def test_update_pulls_then_applies_and_syncs_without_refreshing_downloads(
    tmp_path: Path,
):
    upstream, checkout = tmp_path / "upstream", tmp_path / "rig"
    home, elsewhere, tools = tmp_path / "home", tmp_path / "cwd", tmp_path / "bin"
    for directory in (upstream / "agents", elsewhere, tools):
        directory.mkdir(parents=True)
    (upstream / ".chezmoiroot").write_text("home\n")
    shutil.copytree(REPO / "home/.chezmoiscripts", upstream / "home/.chezmoiscripts")
    shutil.copy2(REPO / "agents/skills.py", upstream / "agents/skills.py")
    manifest = {"version": 1, "sources": [{"source": "owner/pack", "skills": ["one"]}]}
    (upstream / "agents/skills.json").write_text(json.dumps(manifest))
    (upstream / "home/dot_example").write_text("configuration")
    git("init", "--quiet", cwd=upstream)
    git("add", ".", cwd=upstream)
    git("commit", "--quiet", "--message", "Initial", cwd=upstream)
    git("clone", "--quiet", str(upstream), str(checkout), cwd=tmp_path)

    config = home / ".config/chezmoi/chezmoi.json"
    config.parent.mkdir(parents=True)
    config.write_text(
        json.dumps({"sourceDir": str(checkout), "workingTree": str(checkout)})
    )
    fake_bunx(tools)
    (tools / "upstream.txt").write_text("downloaded v1")
    downloads = tools / "downloads.log"
    installed = home / ".agents/skills/one/SKILL.md"
    environment = {
        key: value for key, value in os.environ.items() if not key.startswith("XDG_")
    }
    environment.update(
        HOME=str(home),
        USERPROFILE=str(home),
        UV_CACHE_DIR=str(tmp_path / "uv"),
        PATH=os.pathsep.join([str(tools), os.environ.get("PATH", "")]),
    )

    applied = rig("apply", cwd=elsewhere, env=environment)

    assert applied.returncode == 0, applied.stdout + applied.stderr
    assert installed.read_text() == "downloaded v1"
    assert downloads.read_text().split() == ["one"]

    (tools / "upstream.txt").write_text("downloaded v2")
    head = publish(upstream, "pulled only")

    pulled = rig("update", "--no-apply", cwd=elsewhere, env=environment)

    assert pulled.returncode == 0, pulled.stdout + pulled.stderr
    assert git("rev-parse", "HEAD", cwd=checkout) == head
    assert (home / ".example").read_text() == "configuration"
    assert "Skills sync" not in pulled.stdout + pulled.stderr

    head = publish(upstream, "pulled and applied")

    updated = rig("update", cwd=elsewhere, env=environment)

    assert updated.returncode == 0, updated.stdout + updated.stderr
    assert git("rev-parse", "HEAD", cwd=checkout) == head
    assert (home / ".example").read_text() == "pulled and applied"
    assert updated.stdout.count("Skills sync") == 1
    assert installed.read_text() == "downloaded v1"
    assert downloads.read_text().split() == ["one"]
