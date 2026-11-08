"""Ownership and failure tests use temporary homes; no network or live skills."""

import importlib.util
import io
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location(
    "rig_skills", Path(__file__).parents[1] / "agents/skills.py"
)
skills = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(skills)


class SkillsTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.home = self.base / "home"
        self.repo = self.base / "repo"
        self.repo.mkdir()
        self.manifest = self.repo / "skills.json"
        self.root = self.home / ".agents/skills"
        self.state_file = self.home / ".local/state/rig/skills.json"
        self.args = SimpleNamespace(
            command="sync",
            home=self.home,
            manifest=self.manifest,
            dry_run=False,
            adopt_existing=False,
        )
        self.set_manifest({"owner/pack": ["one"]})

    def set_manifest(self, sources=None):
        skills.save_json(
            self.manifest,
            {
                "version": 1,
                "sources": [
                    {"source": source, "skills": names}
                    for source, names in (sources or {}).items()
                ],
            },
        )

    def write_skill(self, path, content="original"):
        path.mkdir(parents=True, exist_ok=True)
        (path / "SKILL.md").write_text(content)
        return path

    def fetch(self, names, source, stage):
        root = stage / ".agents/skills"
        for name in names:
            self.write_skill(root / name)
        return root

    def run_sync(self, fetch=None, **changes):
        for key, value in changes.items():
            setattr(self.args, key, value)
        output = io.StringIO()
        with (
            patch.object(skills, "REPO", self.repo),
            patch.object(
                skills, "download", side_effect=fetch or self.fetch
            ) as download,
            redirect_stdout(output),
            redirect_stderr(output),
        ):
            result = skills.reconcile(self.args)
        return result, output.getvalue(), download

    def test_missing_installs_existing_sync_is_offline_and_deleted_skill_restores(self):
        self.assertEqual(self.run_sync()[0], 0)
        result, _, download = self.run_sync()
        self.assertEqual(result, 0)
        download.assert_not_called()
        import shutil

        shutil.rmtree(self.root / "one")
        result, _, download = self.run_sync()
        self.assertEqual(result, 0)
        download.assert_called_once()

    def test_claude_copies_preserve_existing_entries_and_track_owned_removal(self):
        claude = self.home / ".claude/skills"
        self.write_skill(claude / "other")
        self.assertEqual(self.run_sync()[0], 0)
        link = claude / "one"
        self.assertTrue(link.is_dir())
        self.assertFalse(link.is_symlink())
        self.assertEqual(skills.digest(link), skills.digest(self.root / "one"))
        self.set_manifest()
        with patch("sys.stdin.isatty", return_value=False):
            self.assertEqual(self.run_sync()[0], 1)
        self.assertTrue(link.is_dir())
        self.assertFalse(link.is_symlink())
        with (
            patch("sys.stdin.isatty", return_value=True),
            patch("builtins.input", return_value="y"),
        ):
            self.assertEqual(self.run_sync()[0], 0)
        self.assertFalse(link.is_symlink())
        self.assertTrue((claude / "other/SKILL.md").exists())

    def test_claude_conflict_is_preserved_and_expected_link_migrates(self):
        claude = self.home / ".claude/skills"
        self.write_skill(claude / "one", "independent")
        self.assertEqual(self.run_sync()[0], 1)
        self.assertEqual((claude / "one/SKILL.md").read_text(), "independent")
        import shutil

        shutil.rmtree(claude / "one")
        (claude / "one").symlink_to(self.root / "one", target_is_directory=True)
        self.assertEqual(self.run_sync()[0], 0)
        self.assertFalse((claude / "one").is_symlink())
        self.assertEqual(
            skills.digest(claude / "one"), skills.digest(self.root / "one")
        )
        self.set_manifest()
        with (
            patch("sys.stdin.isatty", return_value=True),
            patch("builtins.input", return_value="y"),
        ):
            self.assertEqual(self.run_sync()[0], 0)
        self.assertFalse((claude / "one").exists())

    def test_update_refreshes_selected_only_and_preserves_unlisted(self):
        self.run_sync()
        self.write_skill(self.root / "unlisted")

        def newer(names, source, stage):
            for name in names:
                self.write_skill(stage / name, "newer")
            return stage

        result, output, download = self.run_sync(newer, command="update")
        self.assertEqual(result, 0)
        self.assertEqual((self.root / "one/SKILL.md").read_text(), "newer")
        self.assertEqual(
            (self.home / ".claude/skills/one/SKILL.md").read_text(), "newer"
        )
        download.assert_called_once()
        self.assertIn("UNLISTED (untouched): unlisted", output)

    def test_claude_local_edits_survive_shared_update(self):
        self.run_sync()
        target = self.home / ".claude/skills/one/SKILL.md"
        target.write_text("my changes")

        def newer(names, source, stage):
            for name in names:
                self.write_skill(stage / name, "newer")
            return stage

        self.assertEqual(self.run_sync(newer, command="update")[0], 1)
        self.assertEqual(target.read_text(), "my changes")
        self.assertEqual((self.root / "one/SKILL.md").read_text(), "newer")

    def test_claude_migration_rolls_back_if_state_write_fails(self):
        source = self.write_skill(self.root / "one")
        target = self.home / ".claude/skills/one"
        target.parent.mkdir(parents=True)
        target.symlink_to(source, target_is_directory=True)
        results, failures = [], []
        with patch.object(skills, "save_json", side_effect=OSError("disk full")):
            skills.reconcile_claude(
                self.args,
                {"one": {"source": "remote:owner/pack"}},
                self.root,
                results,
                failures,
            )
        self.assertEqual(failures, ["one"])
        self.assertTrue(target.is_symlink())
        self.assertEqual(target.resolve(), source.resolve())

    def test_downloads_once_per_source_with_only_requested_names(self):
        self.set_manifest({"owner/pack": ["one", "two"], "other/pack": ["three"]})
        result, _, download = self.run_sync()
        self.assertEqual(result, 0)
        self.assertEqual(download.call_count, 2)
        self.assertEqual(
            download.call_args_list[0].args[:2], (["one", "two"], "owner/pack")
        )
        self.assertEqual(download.call_args_list[1].args[:2], (["three"], "other/pack"))
        # Sync fetches only a newly added selection, not its installed siblings.
        self.set_manifest(
            {"owner/pack": ["one", "two", "four"], "other/pack": ["three"]}
        )
        result, _, download = self.run_sync()
        self.assertEqual(result, 0)
        download.assert_called_once()
        self.assertEqual(download.call_args.args[:2], (["four"], "owner/pack"))

    def test_unchanged_download_does_not_replace_files_or_rewrite_state(self):
        self.run_sync()
        before = self.state_file.read_bytes()
        with (
            patch.object(skills, "publish") as publish,
            patch.object(skills, "save_json") as save,
        ):
            result, output, _ = self.run_sync(command="update")
        self.assertEqual(result, 0)
        self.assertIn("UNCHANGED one", output)
        publish.assert_not_called()
        save.assert_not_called()
        self.assertEqual(self.state_file.read_bytes(), before)

    def test_failed_source_preserves_its_skills_and_other_sources_continue(self):
        self.set_manifest({"owner/pack": ["one", "two"], "other/pack": ["three"]})
        self.run_sync()

        def failed_source(names, source, stage):
            if source == "owner/pack":
                raise subprocess.CalledProcessError(1, "skills")
            for name in names:
                self.write_skill(stage / name, "updated")
            return stage

        result, _, download = self.run_sync(failed_source, command="update")
        self.assertEqual(result, 1)
        self.assertEqual(download.call_count, 2)
        self.assertEqual((self.root / "one/SKILL.md").read_text(), "original")
        self.assertEqual((self.root / "two/SKILL.md").read_text(), "original")
        self.assertEqual((self.root / "three/SKILL.md").read_text(), "updated")

    def test_results_and_failure_diagnostics_follow_all_downloads(self):
        self.set_manifest({"owner/pack": ["one"], "other/pack": ["two"]})

        def noisy_fetch(names, source, stage):
            print(f"CLI {source}")
            if source == "owner/pack":
                raise subprocess.CalledProcessError(
                    1, "skills", output="\x1b[31mUpstream unavailable\x1b[0m\n"
                )
            return self.fetch(names, source, stage)

        result, output, _ = self.run_sync(noisy_fetch)
        self.assertEqual(result, 1)
        summary = output.index("📋 Skill results")
        self.assertLess(output.index("CLI other/pack"), summary)
        self.assertGreater(output.index("ERROR remote:owner/pack"), summary)
        self.assertGreater(output.index("Upstream unavailable"), summary)
        self.assertGreater(output.index("INSTALLED two"), summary)
        self.assertNotIn("\x1b[", output)

    def test_download_captures_successful_cli_output(self):
        cli = self.base / "fake_cli.py"
        cli.write_text(
            "import sys\nprint('CLI stdout')\nprint('CLI stderr', file=sys.stderr)\n"
        )
        with (
            patch("shutil.which", return_value=sys.executable),
            patch.object(skills, "SKILLS_CLI", str(cli)),
            redirect_stdout(io.StringIO()) as output,
            redirect_stderr(output),
        ):
            skills.download(["one"], "owner/pack", self.base)
        self.assertEqual(output.getvalue(), "")

    def test_partial_failure_keeps_previous_install_and_installs_other_items(self):
        self.run_sync()
        self.set_manifest({"owner/pack": ["one", "two"]})

        def unavailable(names, source, stage):
            for name in names:
                if name != "one":
                    self.write_skill(stage / name)
            return stage

        result, _, _ = self.run_sync(unavailable, command="update")
        self.assertEqual(result, 1)
        self.assertEqual((self.root / "one/SKILL.md").read_text(), "original")
        self.assertTrue((self.root / "two/SKILL.md").is_file())

    def test_local_edits_and_source_changes_are_preserved(self):
        self.run_sync()
        (self.root / "one/SKILL.md").write_text("my edits")
        self.assertEqual(self.run_sync(command="update")[0], 1)
        self.assertEqual((self.root / "one/SKILL.md").read_text(), "my edits")
        self.set_manifest({"someone/else": ["one"]})
        self.assertIn("source changed", self.run_sync()[1])

    def test_custom_source_changes_refresh_but_local_edits_conflict(self):
        custom = self.write_skill(self.repo / "custom/mine")
        self.set_manifest({"./custom": ["mine"]})
        self.assertEqual(self.run_sync()[0], 0)
        (custom / "SKILL.md").write_text("edited in rig")
        self.assertEqual(self.run_sync()[0], 0)
        self.assertEqual((self.root / "mine/SKILL.md").read_text(), "edited in rig")
        (self.root / "mine/SKILL.md").write_text("local edit")
        self.assertEqual(self.run_sync()[0], 1)

    def test_one_local_source_selects_multiple_skills(self):
        self.write_skill(self.repo / "agents/skills/one")
        self.write_skill(self.repo / "agents/skills/two")
        self.set_manifest({"./agents/skills": ["one", "two"]})
        result, _, download = self.run_sync()
        self.assertEqual(result, 0)
        download.assert_not_called()
        records = skills.read_json(self.state_file)["skills"]
        self.assertEqual(records["one"]["source"], "local:agents/skills/one")
        self.assertEqual(records["two"]["source"], "local:agents/skills/two")
        self.assertTrue((self.root / "one/SKILL.md").is_file())
        self.assertTrue((self.root / "two/SKILL.md").is_file())

    def test_owned_download_can_be_explicitly_forked_to_identical_custom_source(self):
        self.run_sync()
        custom = self.write_skill(self.repo / "custom/one")
        self.set_manifest({"./custom": ["one"]})
        self.assertEqual(self.run_sync()[0], 1)
        before = self.state_file.read_bytes()
        self.assertEqual(self.run_sync(adopt_existing=True, dry_run=True)[0], 0)
        self.assertEqual(self.state_file.read_bytes(), before)
        (custom / "SKILL.md").write_text("different source contents")
        self.assertEqual(self.run_sync(dry_run=False)[0], 1)
        self.assertEqual((self.root / "one/SKILL.md").read_text(), "original")
        (custom / "SKILL.md").write_text("original")
        self.assertEqual(self.run_sync()[0], 0)
        self.assertEqual(
            skills.read_json(self.state_file)["skills"]["one"]["source"],
            "local:custom/one",
        )
        (custom / "SKILL.md").write_text("my custom version")
        self.assertEqual(self.run_sync(adopt_existing=False)[0], 0)
        self.assertEqual((self.root / "one/SKILL.md").read_text(), "my custom version")

    def test_removal_requires_confirmation_and_preserves_modified_copies(self):
        self.run_sync()
        self.set_manifest()
        with patch("sys.stdin.isatty", return_value=False):
            self.assertEqual(self.run_sync()[0], 1)
        self.assertTrue((self.root / "one").exists())
        with (
            patch("sys.stdin.isatty", return_value=True),
            patch("builtins.input", return_value="y"),
        ):
            self.assertEqual(self.run_sync()[0], 0)
        self.assertFalse((self.root / "one").exists())

    def test_removing_modified_copy_does_not_prompt(self):
        self.run_sync()
        (self.root / "one/SKILL.md").write_text("modified")
        self.set_manifest()
        with patch("builtins.input") as prompt:
            self.assertEqual(self.run_sync()[0], 1)
            prompt.assert_not_called()

    def test_adoption_requires_explicit_trust_and_matching_source(self):
        self.write_skill(self.root / "one")
        skills.save_json(
            self.home / ".agents/.skill-lock.json",
            {"skills": {"one": {"source": "owner/pack"}}},
        )
        self.assertEqual(self.run_sync()[0], 1)
        self.assertEqual(self.run_sync(adopt_existing=True)[0], 0)
        self.assertIn("one", skills.read_json(self.state_file)["skills"])

    def test_unmanaged_collision_without_metadata_is_preserved(self):
        self.write_skill(self.root / "one", "unknown origin")
        self.assertEqual(self.run_sync(adopt_existing=True)[0], 1)
        self.assertEqual((self.root / "one/SKILL.md").read_text(), "unknown origin")

    def test_dry_run_does_not_download_create_state_or_remove(self):
        result, _, download = self.run_sync(dry_run=True)
        self.assertEqual(result, 0)
        download.assert_not_called()
        self.assertFalse(self.home.exists())

    def test_duplicate_names_and_escaping_custom_paths_rejected(self):
        with self.assertRaises(ValueError):
            skills.selections(
                {
                    "version": 1,
                    "sources": [
                        {"source": "a/b", "skills": ["one"]},
                        {"source": "c/d", "skills": ["ONE"]},
                    ],
                },
                self.repo,
            )
        with self.assertRaises(ValueError):
            skills.selections(
                {
                    "version": 1,
                    "sources": [{"source": "./../escape", "skills": ["one"]}],
                },
                self.repo,
            )

    def test_publish_rolls_back_when_state_write_fails(self):
        self.run_sync()
        before = skills.read_json(self.state_file)
        candidate = self.write_skill(self.base / "incoming", "replacement")
        with (
            patch.object(skills, "save_json", side_effect=OSError("disk full")),
            self.assertRaises(OSError),
        ):
            skills.publish(
                candidate,
                self.root / "one",
                before,
                {"source": "remote:owner/pack", "digest": skills.digest(candidate)},
                self.state_file,
            )
        self.assertEqual((self.root / "one/SKILL.md").read_text(), "original")
        self.assertEqual(before, skills.read_json(self.state_file))

    def test_cli_zero_exit_without_requested_skill_is_rejected(self):
        with patch("shutil.which", return_value="bunx"), patch("subprocess.run"):
            result, _, _ = self.run_sync(fetch=skills.download)
        self.assertEqual(result, 1)
        self.assertFalse((self.root / "one").exists())

    def test_edit_during_download_is_preserved(self):
        self.run_sync()

        def concurrent_edit(names, source, stage):
            for name in names:
                (self.root / name / "SKILL.md").write_text("edited during fetch")
                self.write_skill(stage / name, "downloaded")
            return stage

        result, output, _ = self.run_sync(concurrent_edit, command="update")
        self.assertEqual(result, 1)
        self.assertIn("changed during download", output)
        self.assertEqual(
            (self.root / "one/SKILL.md").read_text(), "edited during fetch"
        )

    def test_concurrent_writer_lock_is_preserved(self):
        lock = self.state_file.with_suffix(".lock")
        lock.parent.mkdir(parents=True)
        lock.write_text("another process")
        with (
            patch("sys.argv", ["skills.py", "sync", "--home", str(self.home)]),
            redirect_stderr(io.StringIO()),
        ):
            self.assertEqual(skills.main(), 1)
        self.assertEqual(lock.read_text(), "another process")
        self.assertFalse(self.root.exists())


if __name__ == "__main__":
    unittest.main()
