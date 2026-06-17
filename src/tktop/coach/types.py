from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

CoachSeverity = Literal["ok", "info", "warn"]


@dataclass(frozen=True)
class CoachFinding:
    category: str
    severity: CoachSeverity
    title: str
    detail: str
    suggestion: str = ""


@dataclass(frozen=True)
class CoachReport:
    score: int
    summary: list[str]
    findings: list[CoachFinding]
    suggested_next_prompt: str
    prompt_pattern: str


@dataclass(frozen=True)
class CoachCacheEntry:
    session_id: str
    fingerprint: str
    report: CoachReport
    local_markdown: str
    enhanced_markdown: str | None = None
    enhanced_provider_label: str | None = None
