import pytest

from tktop.deployment import (
    FetchError,
    ResourceNotFound,
    check_deployment_status,
    deployment_exit_code,
    format_status,
    normalize_version,
)


def test_normalize_version_accepts_plain_or_tagged_semver():
    assert normalize_version("1.2.3") == "1.2.3"
    assert normalize_version("v1.2.3") == "1.2.3"


def test_normalize_version_rejects_invalid_version():
    with pytest.raises(ValueError):
        normalize_version("1.2")


def test_check_deployment_status_reports_deployed_release():
    def fetcher(url: str):
        if "/git/ref/tags/v1.1.3" in url:
            return {"ref": "refs/tags/v1.1.3"}
        if "/actions/runs" in url:
            return {
                "workflow_runs": [
                    {
                        "name": "Release",
                        "head_branch": "v1.1.3",
                        "status": "completed",
                        "conclusion": "success",
                        "html_url": "https://github.example/run/1",
                        "created_at": "2026-06-17T14:20:58Z",
                    }
                ]
            }
        if url == "https://pypi.org/pypi/tktop/json":
            return {"info": {"version": "1.1.3"}, "releases": {"1.1.3": []}}
        raise AssertionError(f"unexpected URL: {url}")

    status = check_deployment_status("1.1.3", fetcher=fetcher)

    assert status.is_deployed
    assert deployment_exit_code(status) == 0
    assert status.github_tag_present is True
    assert status.workflow_conclusion == "success"
    assert status.pypi_version_present is True
    assert "Status: deployed" in format_status(status)


def test_check_deployment_status_uses_version_specific_pypi_endpoint_when_index_lags():
    def fetcher(url: str):
        if "/git/ref/tags/v1.1.3" in url:
            return {"ref": "refs/tags/v1.1.3"}
        if "/actions/runs" in url:
            return {
                "workflow_runs": [
                    {
                        "name": "Release",
                        "head_branch": "v1.1.3",
                        "status": "completed",
                        "conclusion": "success",
                    }
                ]
            }
        if url == "https://pypi.org/pypi/tktop/json":
            return {"info": {"version": "1.1.2"}, "releases": {"1.1.2": []}}
        if url == "https://pypi.org/pypi/tktop/1.1.3/json":
            return {"info": {"version": "1.1.3"}}
        raise AssertionError(f"unexpected URL: {url}")

    status = check_deployment_status("v1.1.3", fetcher=fetcher)

    assert status.is_deployed
    assert status.pypi_latest == "1.1.2"
    assert status.pypi_version_present is True


def test_check_deployment_status_reports_pending_release():
    def fetcher(url: str):
        if "/git/ref/tags/v1.1.3" in url:
            return {"ref": "refs/tags/v1.1.3"}
        if "/actions/runs" in url:
            return {
                "workflow_runs": [
                    {
                        "name": "Release",
                        "head_branch": "v1.1.3",
                        "status": "in_progress",
                        "conclusion": None,
                    }
                ]
            }
        if url == "https://pypi.org/pypi/tktop/json":
            return {"info": {"version": "1.1.2"}, "releases": {"1.1.2": []}}
        if url == "https://pypi.org/pypi/tktop/1.1.3/json":
            raise ResourceNotFound(url)
        raise AssertionError(f"unexpected URL: {url}")

    status = check_deployment_status("1.1.3", fetcher=fetcher)

    assert not status.is_deployed
    assert not status.is_failed
    assert deployment_exit_code(status) == 2
    assert "Status: pending" in format_status(status)


def test_check_deployment_status_reports_failed_workflow():
    def fetcher(url: str):
        if "/git/ref/tags/v1.1.3" in url:
            return {"ref": "refs/tags/v1.1.3"}
        if "/actions/runs" in url:
            return {
                "workflow_runs": [
                    {
                        "name": "Release",
                        "head_branch": "v1.1.3",
                        "status": "completed",
                        "conclusion": "failure",
                    }
                ]
            }
        if url == "https://pypi.org/pypi/tktop/json":
            return {"info": {"version": "1.1.2"}, "releases": {"1.1.2": []}}
        if url == "https://pypi.org/pypi/tktop/1.1.3/json":
            raise ResourceNotFound(url)
        raise AssertionError(f"unexpected URL: {url}")

    status = check_deployment_status("1.1.3", fetcher=fetcher)

    assert status.is_failed
    assert deployment_exit_code(status) == 1
    assert "Status: failed" in format_status(status)


def test_check_deployment_status_keeps_endpoint_errors_visible():
    def fetcher(url: str):
        if "/git/ref/tags/v1.1.3" in url:
            raise FetchError("rate limited")
        if "/actions/runs" in url:
            return {"workflow_runs": []}
        if url == "https://pypi.org/pypi/tktop/json":
            return {"info": {"version": "1.1.3"}, "releases": {"1.1.3": []}}
        raise AssertionError(f"unexpected URL: {url}")

    status = check_deployment_status("1.1.3", fetcher=fetcher)

    assert status.github_tag_present is None
    assert status.github_tag_error == "rate limited"
    assert "rate limited" in format_status(status)
