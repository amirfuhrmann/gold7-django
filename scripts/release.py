#!/usr/bin/env python3
"""
Release management script for Gold7.

Version bumps are controlled explicitly via flags:
- --bump-patch: Bump patch (Z): 1.2.3 → 1.2.4-rc.1
- --bump-minor: Bump minor (Y): 1.2.3 → 1.3.0-rc.1
- --rc-only:    No bump, just increment RC: 1.2.3-rc.1 → 1.2.3-rc.2
- (no flag):    Auto-detect from commits (only MAJOR for breaking changes)

Breaking changes (feat!, fix!, BREAKING CHANGE:) always trigger MAJOR bump.

Usage:
    python scripts/release.py --rc --bump-patch  # Patch release candidate
    python scripts/release.py --rc --bump-minor  # Minor release candidate
    python scripts/release.py --rc --rc-only     # Fix for existing RC
    python scripts/release.py --release          # Promote RC to release
    python scripts/release.py --dry-run          # Show what would happen
"""

import argparse
import re
import subprocess
import sys
from typing import NamedTuple


class Version(NamedTuple):
    major: int
    minor: int
    patch: int
    rc: int | None = None

    def __str__(self) -> str:
        base = f"{self.major}.{self.minor}.{self.patch}"
        if self.rc is not None:
            return f"{base}-rc.{self.rc}"
        return base

    @classmethod
    def parse(cls, version_str: str) -> "Version":
        """Parse version string like '1.2.3' or '1.2.3-rc.1'"""
        version_str = version_str.strip().lstrip("v")

        rc_match = re.match(r"(\d+)\.(\d+)\.(\d+)-rc\.(\d+)", version_str)
        if rc_match:
            return cls(
                major=int(rc_match.group(1)),
                minor=int(rc_match.group(2)),
                patch=int(rc_match.group(3)),
                rc=int(rc_match.group(4)),
            )

        match = re.match(r"(\d+)\.(\d+)\.(\d+)", version_str)
        if match:
            return cls(
                major=int(match.group(1)),
                minor=int(match.group(2)),
                patch=int(match.group(3)),
            )

        raise ValueError(f"Invalid version format: {version_str}")

    def bump_major(self) -> "Version":
        return Version(self.major + 1, 0, 0)

    def bump_minor(self) -> "Version":
        return Version(self.major, self.minor + 1, 0)

    def bump_patch(self) -> "Version":
        return Version(self.major, self.minor, self.patch + 1)

    def to_rc(self, rc_num: int = 1) -> "Version":
        return Version(self.major, self.minor, self.patch, rc_num)

    def bump_rc(self) -> "Version":
        if self.rc is None:
            return self.to_rc(1)
        return Version(self.major, self.minor, self.patch, self.rc + 1)

    def to_release(self) -> "Version":
        return Version(self.major, self.minor, self.patch)

    def base_version(self) -> "Version":
        return Version(self.major, self.minor, self.patch)


class Commit(NamedTuple):
    hash: str
    type: str
    scope: str | None
    breaking: bool
    subject: str
    body: str


def run_git(args: list[str]) -> str:
    result = subprocess.run(
        ["git"] + args, capture_output=True, text=True, check=True,
    )
    return result.stdout.strip()


def fetch_tags() -> None:
    try:
        run_git(["fetch", "--tags", "--force"])
    except subprocess.CalledProcessError:
        pass


def get_last_tag() -> str | None:
    try:
        tags = run_git(["tag", "-l", "v*", "--sort=-v:refname"])
        if tags:
            return tags.split("\n")[0]
        return None
    except subprocess.CalledProcessError:
        return None


def tag_exists(version: Version) -> bool:
    try:
        run_git(["rev-parse", f"v{version}"])
        return True
    except subprocess.CalledProcessError:
        return False


def get_all_tags() -> set[str]:
    try:
        tags = run_git(["tag", "-l", "v*"])
        return set(tags.split("\n")) if tags else set()
    except subprocess.CalledProcessError:
        return set()


def find_next_available_rc(base_version: Version) -> Version:
    existing_tags = get_all_tags()
    highest_rc = 0
    base_str = f"{base_version.major}.{base_version.minor}.{base_version.patch}"
    pattern = re.compile(rf"^v{re.escape(base_str)}-rc\.(\d+)$")

    for tag in existing_tags:
        match = pattern.match(tag)
        if match:
            rc_num = int(match.group(1))
            highest_rc = max(highest_rc, rc_num)

    return base_version.to_rc(highest_rc + 1)


def get_commits_since_tag(tag: str | None, ref: str = "HEAD") -> list[Commit]:
    if tag:
        range_spec = f"{tag}..{ref}"
    else:
        range_spec = ref

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

        commit = parse_conventional_commit(parts[0], parts[1], parts[2] if len(parts) > 2 else "")
        if commit:
            commits.append(commit)

    return commits


def parse_conventional_commit(commit_hash: str, subject: str, body: str) -> Commit | None:
    pattern = r"^(\w+)(?:\(([^)]+)\))?(!)?: (.+)$"
    match = re.match(pattern, subject)

    if not match:
        return Commit(
            hash=commit_hash, type="chore", scope=None,
            breaking=False, subject=subject, body=body,
        )

    commit_type = match.group(1).lower()
    scope = match.group(2)
    breaking_mark = match.group(3) == "!"
    commit_subject = match.group(4)
    breaking = breaking_mark or "BREAKING CHANGE:" in body or "BREAKING-CHANGE:" in body

    return Commit(
        hash=commit_hash, type=commit_type, scope=scope,
        breaking=breaking, subject=commit_subject, body=body,
    )


def determine_bump_type(
    commits: list[Commit],
    force_minor: bool = False,
    force_patch: bool = False,
    rc_only: bool = False,
) -> str:
    if rc_only:
        return "none"
    if force_minor:
        return "minor"
    if force_patch:
        return "patch"
    if any(c.breaking for c in commits):
        return "major"
    return "none"


def get_version_from_tag() -> Version:
    last_tag = get_last_tag()
    if last_tag:
        return Version.parse(last_tag)
    return Version(1, 0, 0)


def generate_release_notes(version: Version, commits: list[Commit]) -> None:
    from pathlib import Path

    release_notes_file = Path(__file__).parent.parent / "RELEASE_NOTES.md"

    grouped: dict[str, list[Commit]] = {
        "feat": [], "fix": [], "perf": [], "breaking": [],
    }

    for commit in commits:
        if commit.breaking:
            grouped["breaking"].append(commit)
        elif commit.type in grouped:
            grouped[commit.type].append(commit)

    lines = [f"# Release {version}\n\n"]

    if grouped["breaking"]:
        lines.append("## Breaking Changes\n\n")
        for commit in grouped["breaking"]:
            lines.append(f"- {commit.subject}\n")
        lines.append("\n")

    if grouped["feat"]:
        lines.append("## New Features\n\n")
        for commit in grouped["feat"]:
            scope = f"**{commit.scope}:** " if commit.scope else ""
            lines.append(f"- {scope}{commit.subject}\n")
        lines.append("\n")

    if grouped["fix"]:
        lines.append("## Bug Fixes\n\n")
        for commit in grouped["fix"]:
            scope = f"**{commit.scope}:** " if commit.scope else ""
            lines.append(f"- {scope}{commit.subject}\n")
        lines.append("\n")

    if grouped["perf"]:
        lines.append("## Performance Improvements\n\n")
        for commit in grouped["perf"]:
            scope = f"**{commit.scope}:** " if commit.scope else ""
            lines.append(f"- {scope}{commit.subject}\n")
        lines.append("\n")

    release_notes_file.write_text("".join(lines))


def main() -> int:
    parser = argparse.ArgumentParser(description="Release management for Gold7")
    parser.add_argument("--rc", action="store_true", help="Create release candidate")
    parser.add_argument("--release", action="store_true", help="Promote RC to stable release")
    parser.add_argument("--dry-run", action="store_true", help="Show what would happen")
    parser.add_argument("--bump-minor", action="store_true", help="Force minor bump (Y)")
    parser.add_argument("--bump-patch", action="store_true", help="Force patch bump (Z)")
    parser.add_argument("--rc-only", action="store_true", help="Only increment RC number")
    args = parser.parse_args()

    bump_flags = sum([args.bump_minor, args.bump_patch, args.rc_only])
    if bump_flags > 1:
        parser.error("Cannot combine --bump-minor, --bump-patch, and --rc-only")

    if not args.rc and not args.release:
        parser.error("Must specify either --rc or --release")

    print("Fetching tags from remote...", file=sys.stderr)
    fetch_tags()

    target_ref = "origin/main"
    print(f"Target ref: {target_ref}", file=sys.stderr)

    last_tag = get_last_tag()
    print(f"Last tag: {last_tag or 'none'}", file=sys.stderr)

    current_version = get_version_from_tag()
    print(f"Current version: {current_version}", file=sys.stderr)

    commits = get_commits_since_tag(last_tag, target_ref)
    print(f"Commits since last tag: {len(commits)}", file=sys.stderr)

    if not commits:
        if args.release and current_version.rc is not None:
            print("Promoting RC to stable release (no new commits needed)", file=sys.stderr)
        else:
            print("No new commits since last tag - nothing to release", file=sys.stderr)
            return 1

    bump_type = determine_bump_type(
        commits, force_minor=args.bump_minor,
        force_patch=args.bump_patch, rc_only=args.rc_only,
    )
    print(f"Bump type: {bump_type}", file=sys.stderr)

    if args.rc:
        base = current_version.base_version()
        if bump_type == "major":
            base_version = base.bump_major()
        elif bump_type == "minor":
            base_version = base.bump_minor()
        elif bump_type == "patch":
            base_version = base.bump_patch()
        else:
            base_version = base
        new_version = find_next_available_rc(base_version)
    else:
        if current_version.rc is not None:
            new_version = current_version.to_release()
        else:
            if bump_type == "major":
                new_version = current_version.bump_major()
            elif bump_type == "minor":
                new_version = current_version.bump_minor()
            else:
                new_version = current_version.bump_patch()

        if tag_exists(new_version):
            print(f"Tag v{new_version} already exists, skipping", file=sys.stderr)
            return 0

    print(f"New version: {new_version}", file=sys.stderr)
    print(f"New tag: v{new_version}", file=sys.stderr)

    if args.dry_run:
        print("\n--- DRY RUN ---", file=sys.stderr)
        print(f"Would create tag: v{new_version}", file=sys.stderr)
        if args.release:
            print("Would generate RELEASE_NOTES.md", file=sys.stderr)
        print("\nCommits to include:", file=sys.stderr)
        for commit in commits[:10]:
            print(f"  - {commit.type}: {commit.subject}", file=sys.stderr)
        if len(commits) > 10:
            print(f"  ... and {len(commits) - 10} more", file=sys.stderr)
        return 0

    print(new_version)

    if args.release:
        generate_release_notes(new_version, commits)
        print("Generated RELEASE_NOTES.md", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
