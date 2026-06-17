#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path

from release_info import read_current_version

VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")


def parse_version(version: str) -> tuple[int, int, int]:
    if not VERSION_RE.fullmatch(version):
        raise ValueError("version must be plain semver like 1.2.3")
    return tuple(int(part) for part in version.split("."))


def tag_exists(repo: Path, tag: str) -> bool:
    result = subprocess.run(
        ["git", "rev-parse", "-q", "--verify", f"refs/tags/{tag}"],
        cwd=repo,
        text=True,
        capture_output=True,
        check=False,
    )
    return result.returncode == 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a target tktop release version")
    parser.add_argument("version", help="Target release version, for example 1.0.1")
    parser.add_argument("--repo", default=".", help="Path to the tktop repository")
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    current = read_current_version(repo)
    target = args.version.strip()
    try:
        current_tuple = parse_version(current)
        target_tuple = parse_version(target)
    except ValueError as exc:
        print(f"Target release version is invalid: {exc}")
        return 2
    tag = f"v{target}"

    problems: list[str] = []
    if target_tuple <= current_tuple:
        problems.append(f"target version {target} must be greater than current {current}")
    if tag_exists(repo, tag):
        problems.append(f"tag already exists locally: {tag}")

    if problems:
        print("Target release version is not ready:")
        for problem in problems:
            print(f"- {problem}")
        return 1

    print(f"Target release version is valid: {target}")
    print(f"Current version: {current}")
    print(f"Release tag: {tag}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
