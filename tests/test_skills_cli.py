"""Run `rig skills` against a temporary checkout, home, and fake skill downloads.

Detailed reconciliation rules live in test_skills.py; these tests check that the
commands reach the active checkout's engine and keep its behavior.
"""

import json
import os
import shutil
import sys
from pathlib import Path

import pytest
from test_cli import REPO, fake_tool, needs_chezmoi_and_uv, rig

# Stands in for `bunx skills@latest add <source> --skill <names...> ...`: copies
# each requested skill from the test's upstream folder and logs the request.
FAKE_BUNX = """\
import json, shutil, sys
from pathlib import Path

args = sys.argv[1:]
names = args[args.index("--skill") + 1 : args.index("--agent")]
upstream = Path(__file__).parent / "upstream"
with (Path(__file__).parent / "downloads.log").open("a") as log:
    print(json.dumps(names), file=log)
for name in names:
    shutil.copytree(upstream / name, Path.cwd() / ".agents/skills" / name)
"""


class Device:
    def __init__(self, base: Path):
        self.checkout, self.home, self.cwd = base / "rig", base / "home", base / "cwd"
        self.tools = base / "tools"
        for directory in (self.cwd, self.tools, self.checkout / "home"):
            directory.mkdir(parents=True)
        shutil.copy2(REPO / "agents/skills.py", self.make(self.checkout / "agents"))
        (self.checkout / ".chezmoiroot").write_text("home\n")
        config = self.make(self.home / ".config/chezmoi") / "chezmoi.json"
        config.write_text(
            json.dumps(
                {"sourceDir": str(self.checkout), "workingTree": str(self.checkout)}
            )
        )
        (self.tools / "fake_bunx.py").write_text(FAKE_BUNX)
        if os.name == "nt":
            (self.tools / "bunx.cmd").write_text(
                f'@"{sys.executable}" "%~dp0fake_bunx.py" %*\n'
            )
        else:
            bunx = self.tools / "bunx"
            bunx.write_text(
                f'#!/bin/sh\nexec "{sys.executable}" "$(dirname "$0")/fake_bunx.py" "$@"\n'
            )
            bunx.chmod(0o755)
        self.env = {
            key: value
            for key, value in os.environ.items()
            if not key.startswith("XDG_")
        }
        self.env.update(
            HOME=str(self.home),
            USERPROFILE=str(self.home),
            UV_CACHE_DIR=str(base / "uv"),
            PATH=os.pathsep.join([str(self.tools), os.environ["PATH"]]),
        )

    @staticmethod
    def make(directory: Path) -> Path:
        directory.mkdir(parents=True, exist_ok=True)
        return directory

    def select(self, downloaded: list[str], custom: list[str]) -> None:
        manifest = {
            "version": 1,
            "sources": [
                {"source": "owner/pack", "skills": downloaded},
                {"source": "./agents/skills", "skills": custom},
            ],
        }
        (self.checkout / "agents/skills.json").write_text(json.dumps(manifest))

    def upstream(self, name: str, content: str) -> None:
        skill = self.make(self.tools / "upstream" / name)
        (skill / "SKILL.md").write_text(content)

    def custom(self, name: str, content: str) -> None:
        skill = self.make(self.checkout / "agents/skills" / name)
        (skill / "SKILL.md").write_text(content)

    def installed(self, name: str, agent: str = ".agents") -> str | None:
        skill = self.home / agent / "skills" / name / "SKILL.md"
        return skill.read_text() if skill.exists() else None

    def downloads(self) -> list[list[str]]:
        log = self.tools / "downloads.log"
        return (
            [json.loads(line) for line in log.read_text().splitlines()]
            if (log.exists())
            else []
        )

    def rig(self, *args: str):
        return rig("skills", *args, cwd=self.cwd, env=self.env)


@pytest.fixture
def device(tmp_path: Path) -> Device:
    return Device(tmp_path)


@needs_chezmoi_and_uv
def test_sync_restores_missing_selections_and_refreshes_custom_but_keeps_downloads(
    device: Device,
):
    device.select(["one"], ["mine"])
    device.upstream("one", "one v1")
    device.custom("mine", "mine v1")

    first = device.rig("sync")

    assert first.returncode == 0, first.stdout + first.stderr
    assert "Skills sync: 2 selected" in first.stdout
    assert device.installed("one") == device.installed("one", ".claude") == "one v1"
    assert device.installed("mine") == "mine v1"

    device.select(["one", "two"], ["mine"])
    device.upstream("one", "one v2")
    device.upstream("two", "two v1")
    device.custom("mine", "mine v2")

    second = device.rig("sync")

    assert second.returncode == 0, second.stdout + second.stderr
    assert device.installed("one") == "one v1"
    assert device.installed("two") == "two v1"
    assert device.installed("mine") == device.installed("mine", ".claude") == "mine v2"
    assert device.downloads() == [["one"], ["two"]]


@needs_chezmoi_and_uv
def test_update_refreshes_selected_downloads_and_keeps_ownership_protections(
    device: Device,
):
    device.select(["one", "two"], [])
    device.upstream("one", "one v1")
    device.upstream("two", "two v1")
    assert device.rig("sync").returncode == 0
    unlisted = device.make(device.home / ".agents/skills/unlisted") / "SKILL.md"
    unlisted.write_text("mine")
    (device.home / ".claude/skills/two/SKILL.md").write_text("local edit")
    device.upstream("one", "one v2")
    device.upstream("two", "two v2")

    result = device.rig("update")

    assert result.returncode == 1
    assert "1 incomplete" in result.stdout
    assert device.installed("one") == device.installed("one", ".claude") == "one v2"
    assert device.installed("two") == "two v2"
    assert device.installed("two", ".claude") == "local edit"
    assert unlisted.read_text() == "mine"


@needs_chezmoi_and_uv
def test_dry_runs_plan_without_downloads_or_writes(device: Device):
    device.select(["one"], [])
    device.upstream("one", "one v1")

    sync_plan = device.rig("sync", "--dry-run")

    assert sync_plan.returncode == 0, sync_plan.stdout + sync_plan.stderr
    assert "WOULD INSTALL one" in sync_plan.stdout
    assert not (device.home / ".agents").exists()
    assert not (device.home / ".local").exists()

    assert device.rig("sync").returncode == 0
    device.upstream("one", "one v2")

    update_plan = device.rig("update", "--dry-run")

    assert update_plan.returncode == 0, update_plan.stdout + update_plan.stderr
    assert "WOULD UPDATE one" in update_plan.stdout
    assert device.installed("one") == "one v1"
    assert device.downloads() == [["one"]]


@needs_chezmoi_and_uv
def test_sync_adopts_matching_existing_copies_only_when_asked(device: Device):
    device.select([], ["mine"])
    device.custom("mine", "mine v1")
    for agent in (".agents", ".claude"):
        existing = device.make(device.home / agent / "skills/mine") / "SKILL.md"
        existing.write_text("mine v1")

    refused = device.rig("sync")
    plan = device.rig("sync", "--adopt-existing", "--dry-run")

    assert refused.returncode == 1
    assert "unmanaged installation" in refused.stdout
    assert plan.returncode == 0, plan.stdout + plan.stderr
    assert "WOULD ADOPT mine" in plan.stdout
    assert not (device.home / ".local/state/rig/skills.json").exists()

    adopted = device.rig("sync", "--adopt-existing")

    assert adopted.returncode == 0, adopted.stdout + adopted.stderr
    assert device.rig("sync").returncode == 0


@pytest.mark.parametrize(
    ("present", "missing", "hint"),
    [
        ([], "chezmoi", "https://www.chezmoi.io/install/"),
        (["chezmoi"], "uv", "https://docs.astral.sh/uv/"),
    ],
)
def test_missing_dependency_stops_with_plain_recovery_step(
    tmp_path: Path, present: list[str], missing: str, hint: str
):
    for tool in present:
        fake_tool(tmp_path, tool)

    result = rig("skills", "sync", env=dict(os.environ, PATH=str(tmp_path)))

    assert result.returncode == 1
    assert result.stdout == ""
    assert f"rig skills sync needs {missing}" in result.stderr
    assert hint in result.stderr
    assert "\x1b[" not in result.stderr


def test_unresolvable_checkout_stops_with_recovery_step(tmp_path: Path):
    fake_tool(tmp_path, "chezmoi", exit_code=1)
    fake_tool(tmp_path, "uv")

    result = rig("skills", "update", env=dict(os.environ, PATH=str(tmp_path)))

    assert result.returncode == 1
    assert "rig skills update could not find the active Rig checkout" in result.stderr
    assert "rig init" in result.stderr
    assert "Traceback" not in result.stderr


def test_unreadable_checkout_paths_stop_with_recovery_step(tmp_path: Path):
    fake_tool(tmp_path, "chezmoi")  # Echoes its arguments instead of JSON.
    fake_tool(tmp_path, "uv")

    result = rig("skills", "sync", env=dict(os.environ, PATH=str(tmp_path)))

    assert result.returncode == 1
    assert "rig skills sync could not read" in result.stderr
    assert "Traceback" not in result.stderr


@needs_chezmoi_and_uv
def test_uninitialized_checkout_stops_with_recovery_step(device: Device):
    (device.checkout / "agents/skills.py").unlink()

    result = device.rig("sync")

    assert result.returncode == 1
    assert "rig skills sync could not find the active Rig checkout" in result.stderr
    assert "no skills engine at" in result.stderr
    assert "rig init" in result.stderr
