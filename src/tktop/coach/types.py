from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

CoachSeverity = Literal["ok", "info", "warn"]
ModelTier = Literal["cheap_fast", "balanced", "strong_reasoning"]
ModelRecommendationConfidence = Literal["low", "medium", "high"]


@dataclass(frozen=True)
class CoachFinding:
    category: str
    severity: CoachSeverity
    title: str
    detail: str
    suggestion: str = ""


@dataclass(frozen=True)
class ModelRecommendation:
    tier: ModelTier
    confidence: ModelRecommendationConfidence
    title: str
    detail: str
    reasons: list[str]
    next_step: str
    escalation_triggers: list[str]


@dataclass(frozen=True)
class CoachReport:
    score: int
    summary: list[str]
    findings: list[CoachFinding]
    suggested_next_prompt: str
    prompt_pattern: str
    model_recommendation: ModelRecommendation | None = None


@dataclass(frozen=True)
class CoachCacheEntry:
    session_id: str
    fingerprint: str
    report: CoachReport
    local_markdown: str
    enhanced_markdown: str | None = None
    enhanced_provider_label: str | None = None
