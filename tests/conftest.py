import pathlib

import pytest

FIXTURES_DIR = pathlib.Path(__file__).parent / "fixtures"


@pytest.fixture
def fixtures_dir() -> pathlib.Path:
    return FIXTURES_DIR


@pytest.fixture
def simple_session_path(fixtures_dir: pathlib.Path) -> pathlib.Path:
    return fixtures_dir / "session_simple.json"


@pytest.fixture
def simple_transcript_path(fixtures_dir: pathlib.Path) -> pathlib.Path:
    return fixtures_dir / "transcript_simple.jsonl"


@pytest.fixture
def tools_transcript_path(fixtures_dir: pathlib.Path) -> pathlib.Path:
    return fixtures_dir / "transcript_with_tools.jsonl"


@pytest.fixture
def drift_transcript_path(fixtures_dir: pathlib.Path) -> pathlib.Path:
    return fixtures_dir / "transcript_drift.jsonl"
