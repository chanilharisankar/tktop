"""Deployment status checks for tktop releases."""

from __future__ import annotations

import argparse
import json
import os
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass
from typing import Any
from urllib.parse import quote

import httpx

from tktop.release import get_current_version, validate_version

DEFAULT_PACKAGE = "tktop"
DEFAULT_REPO = "chanilharisankar/tktop"
DEFAULT_WORKFLOW = "Release"
FAILED_CONCLUSIONS = {
    "action_required",
    "cancelled",
    "failure",
    "skipped",
    "startup_failure",
    "timed_out",
}

JsonFetcher = Callable[[str], dict[str, Any]]


class FetchError(RuntimeError):
    """Raised when a deployment status endpoint cannot be queried."""


class ResourceNotFound(FetchError):
    """Raised when a deployment status endpoint returns 404."""


@dataclass(frozen=True)
class DeploymentStatus:
    package: str
    version: str
    tag: str
    repo: str
    github_tag_present: bool | None
    github_tag_error: str | None
    workflow_name: str
    workflow_status: str | None
    workflow_conclusion: str | None
    workflow_url: str | None
    workflow_created_at: str | None
    workflow_error: str | None
    pypi_latest: str | None
    pypi_version_present: bool | None
    pypi_error: str | None

    @property
    def is_deployed(self) -> bool:
        return (
            self.github_tag_present is True
            and self.workflow_status == "completed"
            and self.workflow_conclusion == "success"
            and self.pypi_version_present is True
        )

    @property
    def is_failed(self) -> bool:
        return self.workflow_conclusion in FAILED_CONCLUSIONS


def normalize_version(version: str) -> str:
    cleaned = version.strip()
    if cleaned.startswith("v"):
        cleaned = cleaned[1:]
    return validate_version(cleaned)


def fetch_json(url: str, *, timeout: float = 10.0) -> dict[str, Any]:
    headers = {"Accept": "application/json", "User-Agent": "tktop-deployment-check"}
    token = os.environ.get("GITHUB_TOKEN")
    if token and url.startswith("https://api.github.com/"):
        headers["Authorization"] = f"Bearer {token}"

    try:
        response = httpx.get(url, headers=headers, timeout=timeout)
        if response.status_code == 404:
            raise ResourceNotFound(url)
        response.raise_for_status()
        data = response.json()
    except ResourceNotFound:
        raise
    except httpx.HTTPStatusError as exc:
        raise FetchError(f"{url}: HTTP {exc.response.status_code}") from exc
    except (httpx.HTTPError, json.JSONDecodeError) as exc:
        raise FetchError(f"{url}: {exc}") from exc

    if not isinstance(data, dict):
        raise FetchError(f"{url}: expected JSON object")
    return data


def check_deployment_status(
    version: str,
    *,
    repo: str = DEFAULT_REPO,
    package: str = DEFAULT_PACKAGE,
    workflow_name: str = DEFAULT_WORKFLOW,
    fetcher: JsonFetcher = fetch_json,
) -> DeploymentStatus:
    normalized = normalize_version(version)
    tag = f"v{normalized}"

    github_tag_present, github_tag_error = _check_github_tag(repo, tag, fetcher)
    workflow_status, workflow_conclusion, workflow_url, workflow_created_at, workflow_error = (
        _check_workflow(repo, tag, workflow_name, fetcher)
    )
    pypi_latest, pypi_version_present, pypi_error = _check_pypi(package, normalized, fetcher)

    return DeploymentStatus(
        package=package,
        version=normalized,
        tag=tag,
        repo=repo,
        github_tag_present=github_tag_present,
        github_tag_error=github_tag_error,
        workflow_name=workflow_name,
        workflow_status=workflow_status,
        workflow_conclusion=workflow_conclusion,
        workflow_url=workflow_url,
        workflow_created_at=workflow_created_at,
        workflow_error=workflow_error,
        pypi_latest=pypi_latest,
        pypi_version_present=pypi_version_present,
        pypi_error=pypi_error,
    )


def wait_for_deployment(
    version: str,
    *,
    repo: str = DEFAULT_REPO,
    package: str = DEFAULT_PACKAGE,
    workflow_name: str = DEFAULT_WORKFLOW,
    timeout_seconds: float = 300.0,
    interval_seconds: float = 10.0,
    fetcher: JsonFetcher = fetch_json,
) -> DeploymentStatus:
    deadline = time.monotonic() + timeout_seconds

    while True:
        status = check_deployment_status(
            version,
            repo=repo,
            package=package,
            workflow_name=workflow_name,
            fetcher=fetcher,
        )
        if status.is_deployed or status.is_failed or time.monotonic() >= deadline:
            return status
        time.sleep(interval_seconds)


def deployment_exit_code(status: DeploymentStatus) -> int:
    if status.is_deployed:
        return 0
    if status.is_failed:
        return 1
    return 2


def format_status(status: DeploymentStatus) -> str:
    lines = [
        f"Deployment status for {status.package} {status.version} ({status.tag})",
        f"- GitHub tag: {_format_bool(status.github_tag_present, status.github_tag_error)}",
        f"- {status.workflow_name} workflow: {_format_workflow(status)}",
        f"- PyPI version: {_format_bool(status.pypi_version_present, status.pypi_error)}",
    ]
    if status.pypi_latest:
        lines.append(f"- PyPI latest: {status.pypi_latest}")
    lines.append(f"Status: {_deployment_label(status)}")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Check tktop release deployment status")
    parser.add_argument(
        "version",
        nargs="?",
        help="release version or tag to check, for example 1.1.3 or v1.1.3",
    )
    parser.add_argument("--repo", default=DEFAULT_REPO, help="GitHub repo as owner/name")
    parser.add_argument("--package", default=DEFAULT_PACKAGE, help="PyPI package name")
    parser.add_argument("--workflow", default=DEFAULT_WORKFLOW, help="GitHub workflow name")
    parser.add_argument(
        "--wait",
        action="store_true",
        help="poll until deployed, failed, or timed out",
    )
    parser.add_argument("--timeout", type=float, default=300.0, help="wait timeout in seconds")
    parser.add_argument(
        "--interval",
        type=float,
        default=10.0,
        help="wait polling interval in seconds",
    )
    parser.add_argument("--json", action="store_true", help="print machine-readable JSON")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    version = args.version or get_current_version()

    if args.wait:
        status = wait_for_deployment(
            version,
            repo=args.repo,
            package=args.package,
            workflow_name=args.workflow,
            timeout_seconds=args.timeout,
            interval_seconds=args.interval,
        )
    else:
        status = check_deployment_status(
            version,
            repo=args.repo,
            package=args.package,
            workflow_name=args.workflow,
        )

    if args.json:
        print(json.dumps(asdict(status), indent=2, sort_keys=True))
    else:
        print(format_status(status))

    return deployment_exit_code(status)


def _check_github_tag(
    repo: str,
    tag: str,
    fetcher: JsonFetcher,
) -> tuple[bool | None, str | None]:
    url = f"https://api.github.com/repos/{repo}/git/ref/tags/{quote(tag, safe='')}"
    try:
        fetcher(url)
    except ResourceNotFound:
        return False, None
    except FetchError as exc:
        return None, str(exc)
    return True, None


def _check_workflow(
    repo: str,
    tag: str,
    workflow_name: str,
    fetcher: JsonFetcher,
) -> tuple[str | None, str | None, str | None, str | None, str | None]:
    url = (
        f"https://api.github.com/repos/{repo}/actions/runs"
        f"?event=push&branch={quote(tag, safe='')}&per_page=20"
    )
    try:
        data = fetcher(url)
    except ResourceNotFound:
        return None, None, None, None, f"repository not found: {repo}"
    except FetchError as exc:
        return None, None, None, None, str(exc)

    runs = data.get("workflow_runs", [])
    if not isinstance(runs, list):
        return None, None, None, None, "unexpected GitHub Actions response"

    matching_runs = [
        run
        for run in runs
        if isinstance(run, dict)
        and run.get("name") == workflow_name
        and run.get("head_branch") == tag
    ]
    if not matching_runs:
        return None, None, None, None, None

    run = matching_runs[0]
    status = _optional_str(run.get("status"))
    conclusion = _optional_str(run.get("conclusion"))
    html_url = _optional_str(run.get("html_url"))
    created_at = _optional_str(run.get("created_at"))
    return status, conclusion, html_url, created_at, None


def _check_pypi(
    package: str,
    version: str,
    fetcher: JsonFetcher,
) -> tuple[str | None, bool | None, str | None]:
    project_url = f"https://pypi.org/pypi/{quote(package, safe='')}/json"
    version_url = f"https://pypi.org/pypi/{quote(package, safe='')}/{version}/json"

    try:
        data = fetcher(project_url)
    except ResourceNotFound:
        return None, False, None
    except FetchError as exc:
        return None, None, str(exc)

    info = data.get("info", {})
    releases = data.get("releases", {})
    latest = info.get("version") if isinstance(info, dict) else None
    present = isinstance(releases, dict) and version in releases
    if present:
        return _optional_str(latest), True, None

    try:
        fetcher(version_url)
    except ResourceNotFound:
        return _optional_str(latest), False, None
    except FetchError as exc:
        return _optional_str(latest), None, str(exc)

    return _optional_str(latest), True, None


def _format_bool(value: bool | None, error: str | None) -> str:
    if error:
        return f"unavailable ({error})"
    if value is True:
        return "found"
    if value is False:
        return "missing"
    return "unknown"


def _format_workflow(status: DeploymentStatus) -> str:
    if status.workflow_error:
        return f"unavailable ({status.workflow_error})"
    if status.workflow_status is None:
        return "not found"

    label = status.workflow_conclusion or status.workflow_status
    details = f"{label} ({status.workflow_status})"
    if status.workflow_url:
        details = f"{details} {status.workflow_url}"
    return details


def _deployment_label(status: DeploymentStatus) -> str:
    if status.is_deployed:
        return "deployed"
    if status.is_failed:
        return "failed"
    return "pending"


def _optional_str(value: Any) -> str | None:
    return value if isinstance(value, str) else None
