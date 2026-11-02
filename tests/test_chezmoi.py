"""Exercise the actual after-script in an isolated chezmoi source and home."""

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).parents[1]


@unittest.skipUnless(
    shutil.which("chezmoi") and shutil.which("uv"), "chezmoi and uv required"
)
class ChezmoiTest(unittest.TestCase):
    def test_apply_refreshes_custom_skills_and_runs_even_without_manifest_changes(self):
        with tempfile.TemporaryDirectory(prefix="rig-integration-") as temporary:
            base = Path(temporary)
            repo, home = base / "repo with spaces", base / "home"
            home.mkdir()
            (repo / "agents/custom/mine").mkdir(parents=True)
            (repo / "home/.chezmoiscripts").mkdir(parents=True)
            (repo / ".chezmoiroot").write_text("home\n")
            shutil.copy2(REPO / "agents/skills.py", repo / "agents/skills.py")
            for hook in (REPO / "home/.chezmoiscripts").iterdir():
                shutil.copy2(hook, repo / "home/.chezmoiscripts" / hook.name)
            manifest = {
                "version": 1,
                "sources": {},
                "custom": {"mine": "agents/custom/mine"},
            }
            (repo / "agents/skills.json").write_text(json.dumps(manifest))
            source = repo / "agents/custom/mine/SKILL.md"
            source.write_text("original")
            (repo / "home/ordinary.txt").write_text("configuration")
            config = base / "config.json"
            config.write_text("{}")
            environment = dict(os.environ, UV_CACHE_DIR=str(base / "uv-cache"))
            command = [
                "chezmoi",
                "--source",
                str(repo),
                "--working-tree",
                str(repo),
                "--destination",
                str(home),
                "--config",
                str(config),
                "--persistent-state",
                str(base / "state.boltdb"),
                "apply",
            ]

            def apply():
                return subprocess.run(
                    command,
                    env=environment,
                    capture_output=True,
                    text=True,
                    timeout=60,
                    check=False,
                )

            first = apply()
            self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
            installed = home / ".agents/skills/mine"
            self.assertEqual((installed / "SKILL.md").read_text(), "original")
            shutil.rmtree(installed)
            source.write_text("edited in rig")
            second = apply()
            self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
            self.assertEqual((installed / "SKILL.md").read_text(), "edited in rig")
            (installed / "SKILL.md").write_text("local conflict")
            (repo / "home/ordinary.txt").write_text("updated configuration")
            conflict = apply()
            self.assertNotEqual(conflict.returncode, 0)
            self.assertEqual((installed / "SKILL.md").read_text(), "local conflict")
            self.assertEqual(
                (home / "ordinary.txt").read_text(), "updated configuration"
            )


if __name__ == "__main__":
    unittest.main()
