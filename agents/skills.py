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
    if not isinstance(manifest.get("sources"), list) or "custom" in manifest:
        raise TypeError("use one sources list with source and skills entries")
    result = {}
    folded = set()

    def add(name, source, local=None):
        if not valid_name(name):
            raise ValueError(f"invalid skill directory name: {name!r}")
        if name.casefold() in folded:
            raise ValueError(f"duplicate skill name: {name}")
        folded.add(name.casefold())
        result[name] = {"source": source, "local": local}

    for entry in manifest["sources"]:
        if not isinstance(entry, dict):
            raise TypeError("each source entry must be an object")
        source, names = entry.get("source"), entry.get("skills")
        if (
            not isinstance(source, str)
            or not source
            or source.startswith("-")
            or not isinstance(names, list)
        ):
            raise ValueError(f"invalid source selection: {source!r}")
        container = None
        if source.startswith("./"):
            container = (repo / source).resolve()
            if not container.is_relative_to(repo.resolve()):
                raise ValueError(f"local source must be inside rig: {source}")
        for name in names:
            if container is None:
                add(name, "remote:" + source)
            else:
                if not valid_name(name):
                    raise ValueError(f"invalid skill directory name: {name!r}")
                local = (container / name).resolve()
                if not local.is_relative_to(container):
                    raise ValueError(f"skill must be inside its local source: {name}")
                relative = local.relative_to(repo.resolve()).as_posix()
                add(name, "local:" + relative, local)
    return result


def download(names, source, staging):
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
            *names,
            "--agent",
            "codex",
            "--yes",
            "--copy",
        ],
        cwd=staging,
        check=True,
        timeout=300,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return staging / ".agents" / "skills"


def publish(candidate, target, state, record, state_file, expected_link=None):
    """Replace one skill and its baseline together; roll back on ordinary errors."""
    with tempfile.TemporaryDirectory(prefix=".rig-", dir=target.parent) as work:
        work = Path(work)
        incoming, backup = work / "new", work / "old"
        shutil.copytree(candidate, incoming)
        old_record = state["skills"].get(target.name)
        had_target = target.exists() or linked(target)
        migrating = (
            expected_link is not None
            and target.is_symlink()
            and target.resolve() == expected_link.resolve()
        )
        if (linked(target) and not migrating) or (
            had_target
            and not migrating
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
        if migrating:
            backup.unlink()


def reconcile_claude(args, selected, root, results, failures):
    destination = args.home / ".claude" / "skills"
    state_dir = args.home / ".local" / "state" / "rig"
    state_file = state_dir / "claude-skills.json"
    state = read_json(state_file) or {"version": 1, "skills": {}}
    if state.get("version") != 1 or not isinstance(state.get("skills"), dict):
        raise ValueError(f"invalid Claude skill state: {state_file}")
    records = state["skills"]
    if any(
        not valid_name(name)
        or not isinstance(record, dict)
        or not isinstance(record.get("source"), str)
        or not isinstance(record.get("digest"), str)
        for name, record in records.items()
    ):
        raise ValueError(f"invalid ownership entries: {state_file}")
    link_file = state_dir / "claude-links.json"
    legacy = read_json(link_file) or {"version": 1, "links": []}
    if (
        legacy.get("version") != 1
        or not isinstance(legacy.get("links"), list)
        or any(not valid_name(name) for name in legacy["links"])
    ):
        raise ValueError(f"invalid Claude link state: {link_file}")

    def matches(link, source):
        return link.is_symlink() and link.resolve() == source.resolve()

    if linked(destination) or (
        destination.exists() and any(destination.glob(".rig-*"))
    ):
        raise ValueError(
            f"linked Claude skills root or interrupted operation; inspect {destination}"
        )
    for name in sorted(selected):
        source, target = root / name, destination / name
        try:
            migrating = matches(target, source)
            previous = records.get(name)
            current = (
                None
                if migrating or not target.exists() and not linked(target)
                else digest(target)
            )
            if previous and current is not None and current != previous["digest"]:
                raise ValueError("local edits detected; preserved")
            if name in failures:
                raise ValueError("shared skill reconciliation failed")
            candidate = selected[name].get("local") if args.dry_run else None
            candidate = candidate if candidate is not None else source
            if args.dry_run and not (candidate / "SKILL.md").is_file():
                results.append(
                    f"CLAUDE WOULD INSTALL {name} (if shared install succeeds)"
                )
                continue
            wanted = digest(candidate)
            record = {"source": selected[name]["source"], "digest": wanted}
            if (
                previous
                and previous["source"] != record["source"]
                and not (args.adopt_existing and current == wanted)
            ):
                raise ValueError("source changed; resolve ownership before replacing")
            if current is not None and not previous:
                if not (args.adopt_existing and current == wanted):
                    raise ValueError(
                        "unmanaged installation; matching content and --adopt-existing required"
                    )
                if not args.dry_run:
                    records[name] = record
                    save_json(state_file, state)
                results.append(
                    f"CLAUDE {'WOULD ADOPT' if args.dry_run else 'ADOPTED'} {name}"
                )
                continue
            if current == wanted and previous:
                if previous != record and not args.dry_run:
                    records[name] = record
                    save_json(state_file, state)
                results.append(f"CLAUDE OK {name}")
                continue
            action = (
                "MIGRATE" if migrating else "INSTALL" if current is None else "UPDATE"
            )
            if args.dry_run:
                results.append(f"CLAUDE WOULD {action} {name}")
                continue
            destination.mkdir(parents=True, exist_ok=True)
            publish(
                source,
                target,
                state,
                record,
                state_file,
                expected_link=source if migrating else None,
            )
            completed = {
                "MIGRATE": "MIGRATED",
                "INSTALL": "INSTALLED",
                "UPDATE": "UPDATED",
            }
            results.append(f"CLAUDE {completed[action]} {name}")
        except (OSError, ValueError) as error:
            failures.append(name)
            results.append(f"CLAUDE ERROR {name}: {error}")

    for name in sorted((set(records) | set(legacy["links"])) - set(selected)):
        target = destination / name
        try:
            if not target.exists() and not linked(target):
                if not args.dry_run:
                    records.pop(name, None)
                    save_json(state_file, state)
                continue
            old_link = name in legacy["links"] and matches(target, root / name)
            if not old_link and (
                name not in records or digest(target) != records[name]["digest"]
            ):
                raise ValueError("local changes detected; removal preserved")
            confirmed = (
                not args.dry_run
                and sys.stdin.isatty()
                and input(f"⚠️ Remove managed Claude skill {name}? [y/N] ")
                .strip()
                .lower()
                == "y"
            )
            if not confirmed:
                results.append(f"CLAUDE REMOVE pending: {name}")
                if not args.dry_run:
                    failures.append(name)
                continue
            if old_link:
                if not matches(target, root / name):
                    raise ValueError("changed during confirmation; preserved")
                target.unlink()
            else:
                if digest(target) != records[name]["digest"]:
                    raise ValueError("changed during confirmation; preserved")
                shutil.rmtree(target)
            records.pop(name, None)
            save_json(state_file, state)
            results.append(f"CLAUDE REMOVED {name}")
        except (OSError, ValueError) as error:
            failures.append(name)
            results.append(f"CLAUDE ERROR {name}: {error}")
    if not args.dry_run and link_file.exists():
        # Retain ownership only for old links still awaiting migration or removal.
        legacy["links"] = [
            name
            for name in legacy["links"]
            if name not in records and (destination / name).is_symlink()
        ]
        save_json(link_file, legacy)


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
    results = []

    def report_error(label, error):
        if isinstance(error, subprocess.CalledProcessError):
            reason = f"skills CLI exited with status {error.returncode}"
        elif isinstance(error, subprocess.TimeoutExpired):
            reason = f"skills CLI timed out after {error.timeout} seconds"
        else:
            reason = str(error)
        results.append(f"❌ ERROR {label}: {reason}")
        details = getattr(error, "stdout", None)
        if isinstance(details, bytes):
            details = details.decode("utf-8", errors="replace")
        if isinstance(details, str) and details.strip():
            # Strip terminal cursor/color sequences from captured CLI diagnostics.
            details = re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", details).strip()
            results.append("\n".join("  " + line for line in details.splitlines()))

    if root.exists() and (linked(root) or any(root.glob(".rig-*"))):
        raise ValueError(
            f"linked skills root or interrupted operation in {root}; inspect before retrying"
        )

    pending = {}
    for name, selection in selected.items():
        target = root / name
        source, local = selection["source"], selection["local"]
        previous = records.get(name)
        try:
            current = digest(target) if target.exists() or target.is_symlink() else None
            if previous and previous["source"] != source:
                if not (
                    args.adopt_existing
                    and local is not None
                    and current == previous["digest"]
                    and current == digest(local)
                ):
                    raise ValueError(
                        "source changed; resolve ownership before replacing"
                    )
                # An explicit, identical local fork can take over an owned copy.
                previous = None
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
                if not args.dry_run:
                    records[name] = {"source": source, "digest": current}
                    save_json(state_file, state)
                results.append(f"{'WOULD ADOPT' if args.dry_run else 'ADOPTED'} {name}")
            refresh = current is None or local is not None or args.command == "update"
            if not refresh:
                results.append(f"OK {name}")
                continue
            if local is not None:
                wanted = digest(local)
                if current == wanted:
                    results.append(f"OK {name}")
                    continue
            if args.dry_run:
                results.append(
                    f"WOULD {'INSTALL' if current is None else 'UPDATE'} {name}"
                )
                continue
            pending.setdefault(source, []).append((name, local, current))
        except (ValueError, OSError, subprocess.SubprocessError) as error:
            failures.append(name)
            report_error(name, error)

    for source, items in pending.items():
        try:
            with tempfile.TemporaryDirectory(prefix="rig-fetch-") as staging:
                downloaded = None
                if items[0][1] is None:
                    downloaded = download(
                        [name for name, _, _ in items],
                        source.removeprefix("remote:"),
                        Path(staging),
                    )
                for name, local, current in items:
                    try:
                        target = root / name
                        candidate = local if local is not None else downloaded / name
                        # Verify each request: the CLI may silently skip missing names.
                        wanted = digest(candidate)
                        actual = (
                            digest(target)
                            if target.exists() or target.is_symlink()
                            else None
                        )
                        if actual != current:
                            raise ValueError(
                                "installation changed during download; preserved"
                            )
                        if wanted == current:
                            results.append(f"UNCHANGED {name}")
                            continue
                        root.mkdir(parents=True, exist_ok=True)
                        record = {"source": source, "digest": wanted}
                        publish(candidate, target, state, record, state_file)
                        results.append(
                            f"{'INSTALLED' if current is None else 'UPDATED'} {name}"
                        )
                    except (ValueError, OSError) as error:
                        failures.append(name)
                        report_error(name, error)
        except (ValueError, OSError, subprocess.SubprocessError) as error:
            failures.extend(name for name, _, _ in items)
            report_error(source, error)

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
            report_error(name, error)
    if removals:
        if not args.dry_run and sys.stdin.isatty():
            print("\n⚠️ Remove managed skills: " + ", ".join(removals), flush=True)
        confirmed = (
            not args.dry_run
            and sys.stdin.isatty()
            and input("⚠️ Remove these managed skills? [y/N] ").strip().lower() == "y"
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
                    results.append(f"REMOVED {name}")
                except (ValueError, OSError) as error:
                    failures.append(name)
                    report_error(name, error)
        else:
            results.append("REMOVE pending: " + ", ".join(removals))
            if not args.dry_run:
                failures.extend(removals)
    reconcile_claude(args, selected, root, results, failures)
    incomplete = len(set(failures))
    action = f"{args.command} plan" if args.dry_run else args.command
    status = "⚠️" if incomplete else "📋" if args.dry_run else "✅"
    print(
        f"{status} Skills {action}: {len(selected)} selected across .agents and .claude; "
        f"{incomplete} incomplete."
    )
    for result in results:
        # Keep diagnostics and pending decisions visible. Dry runs also show plans.
        if result.startswith(("❌ ERROR ", "  ")):
            print(result)
        elif result.startswith("CLAUDE ERROR "):
            print(f"❌ {result}")
        elif result.startswith(("REMOVE pending:", "CLAUDE REMOVE pending:")):
            print(f"⚠️ {result}")
        elif args.dry_run and result.startswith(("WOULD ", "CLAUDE WOULD ")):
            print(f"📋 {result}")
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
        help="adopt matching CLI installs or transfer ownership to an identical custom source",
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
            f"⚠️ Another sync or stale lock exists: {lock}. Inspect before removing it.",
            file=sys.stderr,
        )
        return 1
    except (ValueError, OSError, KeyError, TypeError, EOFError) as error:
        print(f"❌ ERROR: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
