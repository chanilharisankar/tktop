from __future__ import annotations

import dataclasses

from tktop.coach.types import CoachCacheEntry, CoachReport
from tktop.metrics.types import SessionMetrics


def coach_fingerprint(metrics: SessionMetrics) -> str:
    last_turn = metrics.turns[-1] if metrics.turns else None
    last_turn_part = ""
    if last_turn is not None:
        last_turn_part = (
            f"{last_turn.number}:"
            f"{last_turn.role}:"
            f"{last_turn.usage.total}:"
            f"{len(last_turn.tool_calls)}"
        )

    return ":".join(
        [
            metrics.session.id,
            str(len(metrics.turns)),
            str(metrics.total_usage.total),
            str(len(metrics.alerts)),
            metrics.session.updated_at.isoformat(),
            last_turn_part,
        ]
    )


def get_cached_entry(
    cache: dict[str, CoachCacheEntry],
    metrics: SessionMetrics,
) -> CoachCacheEntry | None:
    entry = cache.get(metrics.session.id)
    if entry is None:
        return None
    if entry.fingerprint != coach_fingerprint(metrics):
        return None
    return entry


def build_cache_entry(
    metrics: SessionMetrics,
    report: CoachReport,
    local_markdown: str,
) -> CoachCacheEntry:
    return CoachCacheEntry(
        session_id=metrics.session.id,
        fingerprint=coach_fingerprint(metrics),
        report=report,
        local_markdown=local_markdown,
    )


def with_enhanced_markdown(
    entry: CoachCacheEntry,
    enhanced_markdown: str,
    provider_label: str,
) -> CoachCacheEntry:
    return dataclasses.replace(
        entry,
        enhanced_markdown=enhanced_markdown,
        enhanced_provider_label=provider_label,
    )
