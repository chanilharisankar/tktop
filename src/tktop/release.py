"""Release helper for maintainers.

This module updates the package version, runs verification, creates a release
commit and tag, and optionally pushes them to origin.
"""

from __future__ import annotations

import argparse
import re
import subprocess  # nosec B404 -- release helper runs fixed subprocess commands
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PYPROJECT = ROOT / "pyproject.toml"
VERSION_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")
PROJECT_VERSION_LINE = re.compile(r'(?m)^version = "([^"]+)"$')


def validate_version(version: str) -> str:
    cleaned = version.strip()
    if not VERSION_PATTERN.fullmatch(cleaned):
        raise ValueError(f"invalid version: {version!r}")
    return cleaned


def get_current_version() -> str:
    text = PYPROJECT.read_text()
    match = PROJECT_VERSION_LINE.search(text)
    if match is None:
        raise RuntimeError("could not find project version in pyproject.toml")
    return match.group(1)


def update_version_file(version: str) -> None:
    text = PYPROJECT.read_text()
    updated, count = PROJECT_VERSION_LINE.subn(f'version = "{version}"', text, count=1)
    if count != 1:
        raise RuntimeError("could not update project version in pyproject.toml")
    PYPROJECT.write_text(updated)


def run_command(args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=ROOT,
        check=check,
        text=True,
        capture_output=False,
    )  # nosec B603 -- command list is fixed by the release helper


def capture_command(args: list[str]) -> str:
    result = subprocess.run(
        args,
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )  # nosec B603 -- command list is fixed by the release helper
    return result.stdout.strip()


def ensure_not_already_staged() -> None:
    staged = capture_command(["git", "diff", "--cached", "--name-only"])
    if staged:
        raise RuntimeError(
            "refusing to release with staged changes already present:\n" + staged
        )


def ensure_tag_absent(tag: str) -> None:
    result = subprocess.run(
        ["git", "rev-parse", "-q", "--verify", f"refs/tags/{tag}"],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )  # nosec B603 B607 -- fixed git command and fixed executable name
    if result.returncode == 0:
        raise RuntimeError(f"tag already exists: {tag}")


def release(
    version: str,
    *,
    push: bool = True,
    dry_run: bool = False,
) -> None:
    version = validate_version(version)
    tag = f"v{version}"

    ensure_not_already_staged()
    ensure_tag_absent(tag)

    print(f"releasing {tag}")
    if dry_run:
        print("dry run: no files changed")
        return

    current_version = get_current_version()
    if current_version == version:
        print(f"project version already set to {version}")
    else:
        update_version_file(version)
        print(f"updated pyproject.toml version: {current_version} -> {version}")

    run_command([sys.executable, "-m", "pytest", "-q"])
    run_command([sys.executable, "-m", "build"])

    run_command(["git", "add", "pyproject.toml"])
    run_command(["git", "commit", "-m", f"release: {tag}"])
    run_command(["git", "tag", tag])

    if push:
        run_command(["git", "push", "origin", "HEAD", "--tags"])

    print(f"release complete: {tag}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Prepare and publish a tktop release")
    parser.add_argument("version", help="release version, for example 0.1.1")
    parser.add_argument(
        "--no-push",
        action="store_true",
        help="skip pushing the commit and tag to origin",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="validate inputs without changing files",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    release(args.version, push=not args.no_push, dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
