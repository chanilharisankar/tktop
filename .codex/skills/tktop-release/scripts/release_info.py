#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")
PYPROJECT_VERSION_RE = re.compile(r'(?m)^version = "([^"]+)"$')
FALLBACK_VERSION_RE = re.compile(r'__version__ = "([^"]+)"')


def run(repo: Path, *args: str, check: bool = True) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo,
        text=True,
        capture_output=True,
        check=check,
    )
    return result.stdout.strip()


def read_current_version(repo: Path) -> str:
    pyproject = repo / "pyproject.toml"
    match = PYPROJECT_VERSION_RE.search(pyproject.read_text())
    if match is None:
        raise SystemExit(f"could not find project.version in {pyproject}")
    return match.group(1)


def read_fallback_version(repo: Path) -> str | None:
    init_file = repo / "src" / "tktop" / "__init__.py"
    if not init_file.exists():
        return None
    match = FALLBACK_VERSION_RE.search(init_file.read_text())
    return match.group(1) if match else None


def latest_version_tag(repo: Path) -> str | None:
    tags = run(repo, "tag", "--list", "v[0-9]*.[0-9]*.[0-9]*").splitlines()
    parsed: list[tuple[tuple[int, int, int], str]] = []
    for tag in tags:
        version = tag.removeprefix("v")
        if not VERSION_RE.fullmatch(version):
            continue
        parsed.append((tuple(int(part) for part in version.split(".")), tag))
    if not parsed:
        return None
    return sorted(parsed)[-1][1]


def suggested_versions(version: str) -> dict[str, str]:
    major, minor, patch = (int(part) for part in version.split("."))
    return {
        "patch": f"{major}.{minor}.{patch + 1}",
        "minor": f"{major}.{minor + 1}.0",
        "major": f"{major + 1}.0.0",
    }


def status(repo: Path) -> dict[str, object]:
    current = read_current_version(repo)
    fallback = read_fallback_version(repo)
    short_status = run(repo, "status", "--short", check=True)
    staged = run(repo, "diff", "--cached", "--name-only", check=True)
    return {
        "repo": str(repo),
        "current_version": current,
        "fallback_version": fallback,
        "fallback_matches": fallback in (None, current),
        "latest_tag": latest_version_tag(repo),
        "suggested_versions": suggested_versions(current),
        "dirty": bool(short_status),
        "staged": bool(staged),
        "status": short_status.splitlines(),
    }


def print_human(data: dict[str, object]) -> None:
    print(f"Repository: {data['repo']}")
    print(f"Current version: {data['current_version']}")
    print(f"Fallback __version__: {data['fallback_version'] or 'not found'}")
    print(f"Fallback matches pyproject: {data['fallback_matches']}")
    print(f"Latest local tag: {data['latest_tag'] or 'none'}")
    suggestions = data["suggested_versions"]
    assert isinstance(suggestions, dict)
    print("Suggested next versions:")
    for name in ("patch", "minor", "major"):
        print(f"  {name}: {suggestions[name]}")
    print(f"Dirty worktree: {data['dirty']}")
    print(f"Staged changes: {data['staged']}")
    status_lines = data["status"]
    assert isinstance(status_lines, list)
    if status_lines:
        print("Worktree status:")
        for line in status_lines:
            print(f"  {line}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect tktop release state")
    parser.add_argument("--repo", default=".", help="Path to the tktop repository")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON")
    args = parser.parse_args()

    data = status(Path(args.repo).resolve())
    if args.json:
        print(json.dumps(data, indent=2))
    else:
        print_human(data)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
