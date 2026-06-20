#!/usr/bin/env python3
"""
Generate changelog grouped by release tags.

Modes:
    --full       Generate full retroactive changelog from all tags
    --version X  Generate a single entry for version X (commits since previous tag)

Output:
    src/CHANGELOG.md    — Full changelog (prepended or replaced)
    RELEASE_NOTES.md    — Single entry for GitHub release body

Usage:
    python scripts/generate_changelog.py --full
    python scripts/generate_changelog.py --version 1.0.1
    python scripts/generate_changelog.py --full --dry-run
"""

import argparse
import re
import subprocess
import sys
from collections import OrderedDict
from pathlib import Path


def run_git(args: list[str]) -> str:
    result = subprocess.run(
        ["git"] + args, capture_output=True, text=True, check=True,
    )
    return result.stdout.strip()


def get_all_version_tags() -> list[str]:
    try:
        tags = run_git(["tag", "-l", "v*", "--sort=v:refname"])
        return [t.strip() for t in tags.split("\n") if t.strip()]
    except subprocess.CalledProcessError:
        return []


def get_tag_date(tag: str) -> str:
    try:
        date_str = run_git(["log", "-1", "--format=%ai", tag])
        return date_str[:10]
    except subprocess.CalledProcessError:
        return "unknown"


def get_commits_between(from_ref: str | None, to_ref: str) -> list[dict]:
    range_spec = f"{from_ref}..{to_ref}" if from_ref else to_ref

    try:
        log_output = run_git([
            "log", range_spec, "--format=%H|%s|%b<<<COMMIT>>>",
        ])
    except subprocess.CalledProcessError:
        return []

    commits = []
    for entry in log_output.split("<<<COMMIT>>>"):
        entry = entry.strip()
        if not entry:
            continue

        parts = entry.split("|", 2)
        if len(parts) < 2:
            continue

        commit_hash = parts[0][:8]
        subject = parts[1]
        body = parts[2] if len(parts) > 2 else ""

        pattern = r"^(\w+)(?:\(([^)]+)\))?(!)?: (.+)$"
        match = re.match(pattern, subject)

        if match:
            commit_type = match.group(1).lower()
            scope = match.group(2)
            breaking = match.group(3) == "!" or "BREAKING CHANGE:" in body
            description = match.group(4)
        else:
            if subject.startswith("Merge "):
                continue
            commit_type = "other"
            scope = None
            breaking = False
            description = subject

        commits.append({
            "hash": commit_hash,
            "type": commit_type,
            "scope": scope,
            "breaking": breaking,
            "description": description,
        })

    return commits


TYPE_LABELS = OrderedDict([
    ("breaking", "Breaking Changes"),
    ("feat", "Features"),
    ("fix", "Bug Fixes"),
    ("refactor", "Refactoring"),
    ("perf", "Performance"),
    ("style", "Styling"),
    ("chore", "Maintenance"),
    ("docs", "Documentation"),
    ("other", "Other"),
])


def format_entry(version: str, date: str, commits: list[dict]) -> str:
    grouped: dict[str, list[dict]] = {k: [] for k in TYPE_LABELS}

    for commit in commits:
        if commit["breaking"]:
            grouped["breaking"].append(commit)
        elif commit["type"] in grouped:
            grouped[commit["type"]].append(commit)
        else:
            grouped["other"].append(commit)

    lines = [f"## [{version}] - {date}\n"]

    has_content = False
    for type_key, label in TYPE_LABELS.items():
        if not grouped[type_key]:
            continue
        has_content = True
        lines.append(f"\n### {label}\n")
        for commit in grouped[type_key]:
            scope = f"**{commit['scope']}:** " if commit["scope"] else ""
            lines.append(f"- {scope}{commit['description']} (`{commit['hash']}`)")

    if not has_content:
        lines.append("\n_No notable changes._")

    lines.append("")
    return "\n".join(lines)


def generate_full_changelog(tags: list[str]) -> str:
    entries = []
    prev_tag = None

    for tag in tags:
        version = tag.lstrip("v")
        date = get_tag_date(tag)
        commits = get_commits_between(prev_tag, tag)

        if commits:
            entry = format_entry(version, date, commits)
            entries.append(entry)
        else:
            entries.append(f"## [{version}] - {date}\n\n_No notable changes._\n")

        prev_tag = tag

    entries.reverse()
    return "\n".join(entries)


def write_changelog(content: str, changelog_path: Path) -> None:
    header = "# Changelog\n\nAll notable changes to this project will be documented in this file.\n\n"
    changelog_path.write_text(header + content)


def prepend_entry(entry: str, changelog_path: Path) -> None:
    header = "# Changelog\n\nAll notable changes to this project will be documented in this file.\n"

    if changelog_path.exists():
        existing = changelog_path.read_text()
        if existing.startswith("# Changelog"):
            first_entry = existing.find("\n## ")
            if first_entry != -1:
                existing_entries = existing[first_entry + 1:]
            else:
                existing_entries = ""
        else:
            existing_entries = existing
    else:
        existing_entries = ""

    new_content = header + "\n" + entry
    if existing_entries.strip():
        new_content += "\n" + existing_entries

    changelog_path.write_text(new_content)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate changelog from git tags")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--full", action="store_true", help="Full changelog from all tags")
    mode.add_argument("--version", help="Single entry for this version")
    parser.add_argument("--dry-run", action="store_true", help="Print without writing")
    parser.add_argument("--release-notes-only", action="store_true", help="Only RELEASE_NOTES.md")
    parser.add_argument("--ref", default=None, help="Git ref for --version mode")
    args = parser.parse_args()

    repo_root = Path(__file__).parent.parent
    changelog_path = repo_root / "src" / "CHANGELOG.md"
    release_notes_path = repo_root / "RELEASE_NOTES.md"

    tags = get_all_version_tags()
    if not tags:
        print("No version tags found.", file=sys.stderr)
        return 1

    print(f"Found {len(tags)} tags ({tags[0]} .. {tags[-1]})", file=sys.stderr)

    if args.full:
        content = generate_full_changelog(tags)
        if args.dry_run:
            print(content)
            return 0
        write_changelog(content, changelog_path)
        print(f"Wrote full changelog to {changelog_path}", file=sys.stderr)
        return 0

    # --version mode
    version = args.version
    tag_name = f"v{version}"
    if tag_name in tags:
        idx = tags.index(tag_name)
        prev_tag = tags[idx - 1] if idx > 0 else None
        ref = tag_name
    else:
        prev_tag = tags[-1]
        ref = args.ref or "HEAD"

    date_str = get_tag_date(ref) if ref != "HEAD" else __import__("datetime").datetime.now().strftime("%Y-%m-%d")
    commits = get_commits_between(prev_tag, ref)

    print(f"Commits {prev_tag or 'start'}..{ref}: {len(commits)}", file=sys.stderr)

    entry = format_entry(version, date_str, commits)

    if args.dry_run:
        print(entry)
        return 0

    release_notes_path.write_text(entry)
    print(f"Wrote {release_notes_path}", file=sys.stderr)

    if not args.release_notes_only:
        prepend_entry(entry, changelog_path)
        print(f"Updated {changelog_path}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
