# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Reconcile selected global skills; downloads are staged through Vercel's CLI."""

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SKILLS_CLI = "skills@latest"


def valid_name(name):
    return isinstance(name, str) and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", name)


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def save_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def linked(path):
    return path.is_symlink() or path.is_junction()


def digest(path):
    """Hash relative paths, file contents, and executable bits; reject links."""
    if linked(path) or not path.is_dir():
        raise ValueError(f"not an ordinary skill directory: {path}")
    result = hashlib.sha256()
    for entry in sorted(path.rglob("*")):
        if linked(entry):
            raise ValueError(f"linked content needs manual attention: {entry}")
        if entry.is_file():
            result.update(entry.relative_to(path).as_posix().encode() + b"\0")
            result.update(entry.read_bytes() + b"\0")
            # Windows does not preserve POSIX executable bits.
            if os.name != "nt":
                result.update(str(entry.stat().st_mode & 0o111).encode())
    if not (path / "SKILL.md").is_file():
        raise ValueError(f"missing SKILL.md: {path}")
    return result.hexdigest()


def selections(manifest, repo):
    if not isinstance(manifest, dict) or manifest.get("version") != 1:
        raise ValueError("expected manifest version 1")
    if not isinstance(manifest.get("sources", {}), dict) or not isinstance(
        manifest.get("custom", {}), dict
    ):
        raise TypeError("sources and custom must be objects")
    result = {}
    folded = set()

    def add(name, source, local=None):
        if not valid_name(name):
            raise ValueError(f"invalid skill directory name: {name!r}")
        if name.casefold() in folded:
            raise ValueError(f"duplicate skill name: {name}")
        folded.add(name.casefold())
        result[name] = {"source": source, "local": local}

    for source, names in manifest.get("sources", {}).items():
        if not source or source.startswith("-") or not isinstance(names, list):
            raise ValueError(f"invalid source selection: {source!r}")
        for name in names:
            add(name, "remote:" + source)
    for name, relative in manifest.get("custom", {}).items():
        if not isinstance(relative, str) or not relative:
            raise ValueError(f"invalid custom source for {name}")
        local = (repo / relative).resolve()
        if not local.is_relative_to(repo.resolve()) or local == repo.resolve():
            raise ValueError(f"custom source must be inside rig: {relative}")
        add(name, "local:" + relative, local)
    return result


def download(name, source, staging):
    """Project scope confines CLI file writes to staging, not the global setup."""
    executable = shutil.which("bunx")
    if not executable:
        raise ValueError("bunx is required to download skills; install Bun")
    subprocess.run(
        [
            executable,
            SKILLS_CLI,
            "add",
            source,
            "--skill",
            name,
            "--agent",
            "codex",
            "--yes",
            "--copy",
        ],
        cwd=staging,
        check=True,
        timeout=300,
    )
    candidate = staging / ".agents" / "skills" / name
    digest(candidate)  # A zero exit status alone does not prove installation.
    return candidate


def publish(candidate, target, state, record, state_file):
    """Replace one skill and its baseline together; roll back on ordinary errors."""
    with tempfile.TemporaryDirectory(prefix=".rig-", dir=target.parent) as work:
        work = Path(work)
        incoming, backup = work / "new", work / "old"
        shutil.copytree(candidate, incoming)
        old_record = state["skills"].get(target.name)
        had_target = target.exists()
        if target.is_symlink() or (
            had_target
            and (old_record is None or digest(target) != old_record["digest"])
        ):
            raise ValueError("installation changed during download; preserved")
        if had_target:
            target.rename(backup)
        try:
            incoming.rename(target)
            state["skills"][target.name] = record
            save_json(state_file, state)
        except BaseException:
            if target.exists():
                shutil.rmtree(target)
            if had_target:
                backup.rename(target)
            if old_record is None:
                state["skills"].pop(target.name, None)
            else:
                state["skills"][target.name] = old_record
            raise


def reconcile(args):
    selected = selections(read_json(args.manifest), REPO)
    root = args.home / ".agents" / "skills"
    state_file = args.home / ".local" / "state" / "rig" / "skills.json"
    state = read_json(state_file) or {"version": 1, "skills": {}}
    if state.get("version") != 1 or not isinstance(state.get("skills"), dict):
        raise ValueError(f"invalid local state: {state_file}")
    records = state["skills"]
    if any(
        not valid_name(name)
        or not isinstance(record, dict)
        or not isinstance(record.get("source"), str)
        or not isinstance(record.get("digest"), str)
        for name, record in records.items()
    ):
        raise ValueError(f"invalid ownership entries: {state_file}")
    legacy = read_json(args.home / ".agents" / ".skill-lock.json").get("skills", {})
    failures = []
    if root.exists() and (linked(root) or any(root.glob(".rig-*"))):
        raise ValueError(
            f"linked skills root or interrupted operation in {root}; inspect before retrying"
        )

    for name, selection in selected.items():
        target = root / name
        source, local = selection["source"], selection["local"]
        previous = records.get(name)
        try:
            current = digest(target) if target.exists() or target.is_symlink() else None
            if previous and previous["source"] != source:
                raise ValueError("source changed; resolve ownership before replacing")
            if previous and current and previous["digest"] != current:
                raise ValueError(
                    "local edits detected; preserve or move to a custom skill"
                )
            if current and not previous:
                same_source = legacy.get(name, {}).get("source") == source.removeprefix(
                    "remote:"
                )
                same_custom = local is not None and digest(local) == current
                if not args.adopt_existing or not (same_source or same_custom):
                    raise ValueError(
                        "unmanaged installation; adoption requires matching source and --adopt-existing"
                    )
                print(f"ADOPT {name} (baseline is the current installed content)")
                if not args.dry_run:
                    records[name] = {"source": source, "digest": current}
                    save_json(state_file, state)
            refresh = current is None or local is not None or args.command == "update"
            if not refresh:
                print(f"OK {name}")
                continue
            if local is not None:
                wanted = digest(local)
                if current == wanted:
                    print(f"OK {name}")
                    continue
            print(f"{'INSTALL' if current is None else 'UPDATE'} {name}")
            if args.dry_run:
                continue
            root.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryDirectory(prefix="rig-fetch-") as staging:
                candidate = local or download(
                    name, source.removeprefix("remote:"), Path(staging)
                )
                record = {"source": source, "digest": digest(candidate)}
                publish(candidate, target, state, record, state_file)
        except (ValueError, OSError, subprocess.SubprocessError) as error:
            failures.append(name)
            print(f"ERROR {name}: {error}", file=sys.stderr)

    removals = []
    for name in sorted(set(records) - set(selected)):
        target = root / name
        try:
            if target.exists() or target.is_symlink():
                if digest(target) != records[name]["digest"]:
                    raise ValueError("local edits detected; removal preserved")
                removals.append(name)
            elif not args.dry_run:
                del records[name]
                save_json(state_file, state)
        except (ValueError, OSError) as error:
            failures.append(name)
            print(f"ERROR {name}: {error}", file=sys.stderr)
    if removals:
        print("REMOVE pending: " + ", ".join(removals))
        confirmed = (
            not args.dry_run
            and sys.stdin.isatty()
            and input("Remove these managed skills? [y/N] ").strip().lower() == "y"
        )
        if confirmed:
            for name in removals:
                try:
                    # Recheck after confirmation before deleting anything.
                    if digest(root / name) != records[name]["digest"]:
                        raise ValueError("changed during confirmation; preserved")
                    shutil.rmtree(root / name)
                    del records[name]
                    save_json(state_file, state)
                    print(f"REMOVED {name}")
                except (ValueError, OSError) as error:
                    failures.append(name)
                    print(f"ERROR {name}: {error}", file=sys.stderr)
        elif not args.dry_run:
            failures.extend(removals)
    if root.exists():
        unlisted = sorted(
            p.name
            for p in root.iterdir()
            if not p.name.startswith(".")
            and p.name not in selected
            and p.name not in records
        )
        if unlisted:
            print("UNLISTED (untouched): " + ", ".join(unlisted))
    print(f"Skills: {len(selected)} selected; {len(set(failures))} incomplete.")
    return int(bool(failures))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["sync", "update"])
    parser.add_argument(
        "--manifest", type=Path, default=REPO / "agents" / "skills.json"
    )
    parser.add_argument(
        "--home",
        type=Path,
        default=Path.home(),
        help="destination home (also scopes ownership state)",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--adopt-existing",
        action="store_true",
        help="trust current contents when existing CLI source metadata matches",
    )
    args = parser.parse_args()
    # Refuse simultaneous writers, including sync versus explicit update.
    lock = args.home / ".local" / "state" / "rig" / "skills.lock"
    try:
        if args.dry_run:
            return reconcile(args)
        lock.parent.mkdir(parents=True, exist_ok=True)
        with lock.open("x", encoding="utf-8") as stream:
            stream.write(str(os.getpid()))
        try:
            return reconcile(args)
        finally:
            lock.unlink()
    except FileExistsError:
        print(
            f"Another sync or stale lock exists: {lock}. Inspect before removing it.",
            file=sys.stderr,
        )
        return 1
    except (ValueError, OSError, KeyError, TypeError, EOFError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
