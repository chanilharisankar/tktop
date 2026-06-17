from __future__ import annotations

import re

from tktop.coach.types import ModelRecommendation
from tktop.metrics.types import SessionMetrics

SIMPLE_TASK_RE = re.compile(
    r"\b(typo|spelling|grammar|readme|docs?|markdown|comment|comments|"
    r"formatting|format|rename|copy|text|changelog)\b",
    re.IGNORECASE,
)
CONFIG_TASK_RE = re.compile(
    r"\b(config|toml|yaml|yml|json|env|setting|settings)\b",
    re.IGNORECASE,
)
BUG_TASK_RE = re.compile(
    r"\b(bug|fix|debug|failing|failure|error|exception|regression|test)\b",
    re.IGNORECASE,
)
STRONG_TASK_RE = re.compile(
    r"\b(architecture|architect|design|migration|migrate|refactor|security|"
    r"permission|concurrency|race|deadlock|performance|scalability|"
    r"distributed|intermittent|flaky|ambiguous|root cause|incident|"
    r"data model|schema|plugin architecture)\b",
    re.IGNORECASE,
)
FILE_SCOPE_RE = re.compile(
    r"(\b[\w.-]+/[\w./-]+|[\w.-]+\.(py|js|ts|tsx|jsx|md|toml|json|yaml|yml)|"
    r"\b(src|tests|docs|scripts)/)",
    re.IGNORECASE,
)
VALIDATION_RE = re.compile(
    r"\b(pytest|tests?|make\s+test|make\s+check|ruff|mypy|npm\s+test|"
    r"pnpm\s+test|verify|validation|lint)\b",
    re.IGNORECASE,
)

CHEAP_NEXT_STEP = (
    "Start with your cheapest fast coding model. Escalate only if it needs to "
    "inspect several modules, reason through failing behavior, or make design tradeoffs."
)
BALANCED_NEXT_STEP = (
    "Start with your balanced coding model. Escalate to a strong reasoning model only "
    "if the agent gets stuck, crosses many modules, or starts looping."
)
STRONG_NEXT_STEP = (
    "Start with your strongest reasoning model or split the task into a discovery pass "
    "first. De-escalate after the design, root cause, or migration plan is clear."
)


def recommend_model_tier(metrics: SessionMetrics) -> ModelRecommendation | None:
    user_turns = [turn for turn in metrics.turns if turn.role == "user"]
    assistant_turns = [turn for turn in metrics.turns if turn.role == "assistant"]
    if not user_turns and not assistant_turns:
        return None

    user_text = "\n".join(turn.content_preview for turn in user_turns)
    tool_calls = sum(stat.calls for stat in metrics.tool_stats.values())
    broad_session = _is_broad_session(metrics, user_text, tool_calls)

    strong_reasons = _strong_reasons(metrics, user_text, tool_calls, broad_session)
    if strong_reasons:
        return ModelRecommendation(
            tier="strong_reasoning",
            confidence=_confidence(strong_reasons),
            title="Use a strong reasoning model",
            detail=(
                "This session looks complex, ambiguous, broad, or drift-prone enough "
                "that a cheaper model may spend more tokens exploring than it saves."
            ),
            reasons=strong_reasons,
            next_step=STRONG_NEXT_STEP,
            escalation_triggers=[],
        )

    cheap_reasons = _cheap_reasons(metrics, user_text, tool_calls)
    if cheap_reasons:
        return ModelRecommendation(
            tier="cheap_fast",
            confidence=_confidence(cheap_reasons),
            title="Use a cheaper fast model",
            detail=(
                "This looks narrow and low-risk enough that starting with a premium "
                "reasoning model is probably unnecessary."
            ),
            reasons=cheap_reasons,
            next_step=CHEAP_NEXT_STEP,
            escalation_triggers=_default_escalation_triggers(),
        )

    reasons = _balanced_reasons(metrics, user_text, tool_calls, broad_session)
    return ModelRecommendation(
        tier="balanced",
        confidence=_confidence(reasons),
        title="Use a balanced coding model",
        detail=(
            "This looks like ordinary implementation or debugging work where a balanced "
            "model should handle the first pass without starting at the highest-cost tier."
        ),
        reasons=reasons,
        next_step=BALANCED_NEXT_STEP,
        escalation_triggers=_default_escalation_triggers(),
    )


def _strong_reasons(
    metrics: SessionMetrics,
    user_text: str,
    tool_calls: int,
    broad_session: bool,
) -> list[str]:
    reasons: list[str] = []
    if STRONG_TASK_RE.search(user_text):
        reasons.append(
            "Prompt language points to architecture, migration, security, or hard debugging."
        )
    if len(metrics.alerts) >= 2:
        reasons.append(
            "Multiple drift alerts appeared, so stronger reasoning or smaller task splits may help."
        )
    elif metrics.alerts and (len(metrics.turns) >= 20 or tool_calls >= 20):
        reasons.append("The session combined drift alerts with high activity.")
    if broad_session and (len(metrics.turns) >= 20 or tool_calls >= 15):
        reasons.append("Broad scope plus many turns/tool calls suggests expensive discovery.")
    if metrics.total_usage.billable >= 80_000:
        reasons.append("Billable token volume was high enough to justify better initial reasoning.")
    return reasons


def _cheap_reasons(metrics: SessionMetrics, user_text: str, tool_calls: int) -> list[str]:
    reasons: list[str] = []
    simple_task = bool(SIMPLE_TASK_RE.search(user_text))
    config_task = bool(CONFIG_TASK_RE.search(user_text))
    bug_task = bool(BUG_TASK_RE.search(user_text))

    if SIMPLE_TASK_RE.search(user_text):
        reasons.append(
            "Prompt language points to docs, text, formatting, or a small mechanical edit."
        )
    if config_task and not bug_task:
        reasons.append("Configuration-only work usually does not require the strongest model.")
    if _has_scope(user_text):
        reasons.append("The prompt names a file, module, or test path.")
    if _has_validation(user_text):
        reasons.append("The prompt includes a validation signal.")
    if len(metrics.turns) <= 8 and tool_calls <= 6 and not metrics.alerts:
        reasons.append("The session stayed short with low tool usage and no drift alerts.")

    if not reasons:
        return []

    if bug_task and not (simple_task or config_task):
        return []
    if STRONG_TASK_RE.search(user_text) or len(metrics.turns) > 12 or tool_calls > 10:
        return []
    return reasons


def _balanced_reasons(
    metrics: SessionMetrics,
    user_text: str,
    tool_calls: int,
    broad_session: bool,
) -> list[str]:
    reasons: list[str] = []
    if BUG_TASK_RE.search(user_text):
        reasons.append("Prompt language points to implementation or focused debugging.")
    if _has_scope(user_text):
        reasons.append("The task has some file or module scope.")
    if _has_validation(user_text):
        reasons.append("The prompt includes a validation path.")
    if metrics.alerts:
        reasons.append(
            "There was a drift signal, but not enough evidence to start at the strongest tier."
        )
    if broad_session:
        reasons.append(
            "The prompt was somewhat broad, but the session did not cross strong-tier thresholds."
        )
    if tool_calls:
        reasons.append(
            f"The session used {tool_calls} tool calls, which fits normal coding-agent work."
        )
    if not reasons:
        reasons.append("No strong cheap-task or strong-reasoning signal dominated the session.")
    return reasons


def _is_broad_session(metrics: SessionMetrics, user_text: str, tool_calls: int) -> bool:
    return (
        not _has_scope(user_text)
        or len(metrics.turns) >= 15
        or tool_calls >= 12
        or metrics.total_usage.billable >= 40_000
    )


def _has_scope(text: str) -> bool:
    return bool(FILE_SCOPE_RE.search(text))


def _has_validation(text: str) -> bool:
    return bool(VALIDATION_RE.search(text))


def _confidence(reasons: list[str]) -> str:
    if len(reasons) >= 3:
        return "high"
    if len(reasons) == 2:
        return "medium"
    return "low"


def _default_escalation_triggers() -> list[str]:
    return [
        "The agent needs to reason across several modules or services.",
        "The first pass finds a flaky, security-sensitive, or ambiguous root cause.",
        "Tool usage starts looping or broad exploration continues before edits.",
    ]
