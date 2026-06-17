from __future__ import annotations

import re

from tktop.coach.model_advisor import recommend_model_tier
from tktop.coach.types import CoachFinding, CoachReport
from tktop.metrics.types import SessionMetrics, Turn

VAGUE_PROMPT_RE = re.compile(
    r"\b(fix|improve|clean\s*up|make\s+better|handle|update|do\s+this|check)\b",
    re.IGNORECASE,
)
FILE_SCOPE_RE = re.compile(
    r"(\b[\w.-]+/[\w./-]+|[\w.-]+\.(py|js|ts|tsx|jsx|md|toml|json|yaml|yml)|"
    r"\b(src|tests|docs|scripts)/)",
    re.IGNORECASE,
)
TEST_RE = re.compile(
    r"\b(pytest|tests?|make\s+test|make\s+check|ruff|mypy|npm\s+test|"
    r"pnpm\s+test|verify|validation|lint)\b",
    re.IGNORECASE,
)
TEST_COMMAND_RE = re.compile(
    r"\b(pytest|make\s+test|make\s+check|ruff|mypy|npm\s+test|pnpm\s+test|lint)\b",
    re.IGNORECASE,
)
ACCEPTANCE_RE = re.compile(
    r"\b(acceptance|criteria|done\s+when|success|expected|should|must|verify|pass)\b",
    re.IGNORECASE,
)
CHECKPOINT_RE = re.compile(
    r"\b(checkpoint|summarize|summary|recap|status|stop\s+and|pause)\b",
    re.IGNORECASE,
)

EXPLORATION_TOOLS = {"read", "grep", "glob", "ls", "search", "find"}
EDIT_TOOLS = {"edit", "write", "multiedit", "notebookedit"}


def build_coach_report(metrics: SessionMetrics) -> CoachReport:
    user_turns = [turn for turn in metrics.turns if turn.role == "user"]
    assistant_text = "\n".join(
        turn.content_preview for turn in metrics.turns if turn.role == "assistant"
    )
    user_text = "\n".join(turn.content_preview for turn in user_turns)
    findings: list[CoachFinding] = []

    if not metrics.turns:
        return CoachReport(
            score=0,
            summary=["No transcript turns were available for coaching."],
            findings=[
                CoachFinding(
                    category="Workflow Habits",
                    severity="info",
                    title="No session activity found",
                    detail="tktop could not find transcript turns for this session.",
                    suggestion="Open a session with transcript data before using Coach.",
                )
            ],
            suggested_next_prompt=(
                "Start a focused session and include the goal, scope, validation, "
                "and stop condition."
            ),
            prompt_pattern=_prompt_pattern(),
            model_recommendation=None,
        )

    first_prompt = user_turns[0].content_preview if user_turns else ""
    has_scope = bool(FILE_SCOPE_RE.search(user_text))
    has_tests = bool(TEST_RE.search(user_text) or TEST_COMMAND_RE.search(assistant_text))
    has_acceptance = bool(ACCEPTANCE_RE.search(user_text))
    has_checkpoint = bool(CHECKPOINT_RE.search(user_text))
    first_prompt_is_broad = _is_broad_prompt(first_prompt)

    if first_prompt_is_broad:
        findings.append(
            CoachFinding(
                category="Prompt Habits",
                severity="warn",
                title="First prompt was broad",
                detail=(
                    "The opening prompt did not give much scope, validation, or "
                    "success criteria. Broad starts usually make agents explore more."
                ),
                suggestion=(
                    "Start with the target area, expected behavior, validation command, "
                    "and a clear stop condition."
                ),
            )
        )
    elif first_prompt:
        findings.append(
            CoachFinding(
                category="Prompt Habits",
                severity="ok",
                title="First prompt had enough shape to begin",
                detail="The opening prompt was not flagged as vague or underspecified.",
            )
        )

    if not has_scope:
        findings.append(
            CoachFinding(
                category="Prompt Habits",
                severity="warn",
                title="No file or module scope detected",
                detail=(
                    "The user prompts did not mention specific files, directories, "
                    "modules, or tests."
                ),
                suggestion="Name the most relevant file, package, or test path when possible.",
            )
        )

    if not has_acceptance:
        findings.append(
            CoachFinding(
                category="Prompt Habits",
                severity="warn",
                title="No acceptance criteria detected",
                detail=(
                    "The prompts did not clearly state what should be true when the "
                    "agent is finished."
                ),
                suggestion="Add a short success condition such as 'stop after tests pass'.",
            )
        )

    if has_tests:
        findings.append(
            CoachFinding(
                category="Validation Habits",
                severity="ok",
                title="Testing or validation was mentioned",
                detail="The session included a test, lint, verify, or validation signal.",
            )
        )
    else:
        findings.append(
            CoachFinding(
                category="Validation Habits",
                severity="warn",
                title="No test or validation signal detected",
                detail=(
                    "Coach did not find test, lint, verify, or validation language in "
                    "the visible prompts or previews."
                ),
                suggestion=(
                    "Tell the agent which focused test or validation command should run."
                ),
            )
        )

    exploration_before_edit = _count_exploration_before_first_edit(metrics.turns)
    if exploration_before_edit >= 8:
        findings.append(
            CoachFinding(
                category="Workflow Habits",
                severity="warn",
                title="Heavy exploration before first edit",
                detail=(
                    f"The agent made {exploration_before_edit} exploration tool calls "
                    "before the first edit-like tool call."
                ),
                suggestion=(
                    "Provide likely files or a focused search target so the agent can "
                    "start closer to the change."
                ),
            )
        )

    repeated_tool = _dominant_tool(metrics)
    if repeated_tool is not None:
        name, calls, pct = repeated_tool
        findings.append(
            CoachFinding(
                category="Workflow Habits",
                severity="warn",
                title=f"{name} dominated tool usage",
                detail=f"{name} accounted for {calls} calls ({pct:.0f}% of tool usage).",
                suggestion=(
                    "If this was not expected, narrow the prompt or ask for a checkpoint "
                    "before more exploration."
                ),
            )
        )

    if _needs_checkpoint(metrics) and not has_checkpoint:
        findings.append(
            CoachFinding(
                category="Checkpoint Habits",
                severity="warn",
                title="Long session without a checkpoint prompt",
                detail=(
                    f"This session has {len(metrics.turns)} turns and "
                    f"{metrics.total_usage.billable:,} billable tokens."
                ),
                suggestion=(
                    "Ask the agent to stop and summarize files changed, tests run, "
                    "risks, and the smallest next step."
                ),
            )
        )
    elif has_checkpoint:
        findings.append(
            CoachFinding(
                category="Checkpoint Habits",
                severity="ok",
                title="Checkpoint language was used",
                detail="The prompts included summary, status, checkpoint, or pause language.",
            )
        )

    if first_prompt_is_broad and _early_output_tokens(metrics.turns) >= 5_000:
        findings.append(
            CoachFinding(
                category="Efficiency Habits",
                severity="warn",
                title="Broad prompt led into high early output",
                detail=(
                    "The first assistant turns produced substantial output after a broad "
                    "opening prompt."
                ),
                suggestion="Split discovery and implementation into separate, smaller asks.",
            )
        )

    summary = [
        f"{len(metrics.turns)} turns",
        f"{metrics.total_usage.billable:,} billable tokens",
        f"${metrics.total_cost:.2f} estimated API-equivalent cost",
        f"{sum(stat.calls for stat in metrics.tool_stats.values())} tool calls",
        f"{len(metrics.alerts)} drift alerts",
    ]

    return CoachReport(
        score=_score(findings),
        summary=summary,
        findings=findings,
        suggested_next_prompt=_suggest_next_prompt(
            has_tests=has_tests,
            has_scope=has_scope,
            has_acceptance=has_acceptance,
            needs_checkpoint=_needs_checkpoint(metrics),
        ),
        prompt_pattern=_prompt_pattern(),
        model_recommendation=recommend_model_tier(metrics),
    )


def render_coach_markdown(report: CoachReport) -> str:
    lines = [
        "# Coach",
        "",
        f"**Session Usage Score:** {report.score}/100",
        "",
        "## Session Summary",
        *[f"- {item}" for item in report.summary],
        "",
    ]

    if report.model_recommendation is not None:
        recommendation = report.model_recommendation
        lines.extend(
            [
                "## Model Fit",
                "",
                f"**Recommended tier:** `{recommendation.tier}`",
                f"**Confidence:** {recommendation.confidence}",
                "",
                recommendation.detail,
                "",
                "**Why:**",
                *[f"- {reason}" for reason in recommendation.reasons],
                "",
                "**Next time:**",
                recommendation.next_step,
            ]
        )
        if recommendation.escalation_triggers:
            lines.extend(
                [
                    "",
                    "**Escalate when:**",
                    *[
                        f"- {trigger}"
                        for trigger in recommendation.escalation_triggers
                    ],
                ]
            )
        lines.append("")

    for category in _categories(report.findings):
        lines.extend([f"## {category}", ""])
        for finding in [f for f in report.findings if f.category == category]:
            label = finding.severity.upper()
            lines.append(f"- **{label}: {finding.title}**")
            lines.append(f"  {finding.detail}")
            if finding.suggestion:
                lines.append(f"  Suggestion: {finding.suggestion}")
        lines.append("")

    lines.extend(
        [
            "## Suggested Next Prompt",
            "",
            "```text",
            report.suggested_next_prompt,
            "```",
            "",
            "## Better Prompt Pattern",
            "",
            "```text",
            report.prompt_pattern,
            "```",
        ]
    )
    return "\n".join(lines)


def _is_broad_prompt(prompt: str) -> bool:
    text = prompt.strip()
    if not text:
        return False
    has_scope = bool(FILE_SCOPE_RE.search(text))
    has_tests = bool(TEST_RE.search(text))
    has_acceptance = bool(ACCEPTANCE_RE.search(text))
    vague = bool(VAGUE_PROMPT_RE.search(text))
    return (len(text) < 80 and vague) or (vague and not (has_scope or has_tests or has_acceptance))


def _count_exploration_before_first_edit(turns: list[Turn]) -> int:
    count = 0
    for turn in turns:
        for tool_call in turn.tool_calls:
            tool = tool_call.name.lower()
            if tool in EDIT_TOOLS:
                return count
            if tool in EXPLORATION_TOOLS:
                count += 1
    return count


def _dominant_tool(metrics: SessionMetrics) -> tuple[str, int, float] | None:
    total_calls = sum(stat.calls for stat in metrics.tool_stats.values())
    if total_calls < 10:
        return None
    stat = max(metrics.tool_stats.values(), key=lambda item: item.calls)
    pct = stat.calls / total_calls * 100
    if stat.calls >= 10 and pct >= 50:
        return stat.name, stat.calls, pct
    return None


def _needs_checkpoint(metrics: SessionMetrics) -> bool:
    return len(metrics.turns) >= 30 or metrics.total_usage.billable >= 100_000


def _early_output_tokens(turns: list[Turn]) -> int:
    assistant_turns = [turn for turn in turns if turn.role == "assistant"]
    return sum(turn.usage.output_tokens for turn in assistant_turns[:3])


def _score(findings: list[CoachFinding]) -> int:
    penalty = 0
    for finding in findings:
        if finding.severity == "warn":
            penalty += 10
    return max(0, min(100, 100 - penalty))


def _suggest_next_prompt(
    *,
    has_tests: bool,
    has_scope: bool,
    has_acceptance: bool,
    needs_checkpoint: bool,
) -> str:
    if needs_checkpoint:
        return (
            "Stop and summarize files changed, tests run, remaining risks, and "
            "the smallest next step."
        )
    if not has_tests:
        return (
            "Run the focused validation command for this change, report failures, "
            "and stop after the smallest fix."
        )
    if not has_scope or not has_acceptance:
        return (
            "For the next change, work only in <files or module>, validate with "
            "<command>, and stop when <success condition> is true."
        )
    return (
        "Summarize the result, list tests run, call out remaining risks, and suggest "
        "one small next step."
    )


def _prompt_pattern() -> str:
    return "\n".join(
        [
            "Goal: <specific change or question>",
            "Scope: <files, modules, or tests to start with>",
            "Constraints: <what not to change>",
            "Validation: <focused command or check>",
            "Stop condition: <when to stop and report back>",
        ]
    )


def _categories(findings: list[CoachFinding]) -> list[str]:
    preferred = [
        "Prompt Habits",
        "Validation Habits",
        "Workflow Habits",
        "Checkpoint Habits",
        "Efficiency Habits",
    ]
    present = {finding.category for finding in findings}
    ordered = [category for category in preferred if category in present]
    ordered.extend(sorted(present - set(ordered)))
    return ordered
