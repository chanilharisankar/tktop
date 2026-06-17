from __future__ import annotations

from tktop.coach.types import CoachReport
from tktop.metrics.types import SessionMetrics

SYSTEM_PROMPT = """\
You are a practical coach for developers using agentic coding tools. Your job is to help \
the developer improve how they scope, prompt, checkpoint, and validate work with coding \
agents.

Focus only on developer-controllable behavior:
- prompt clarity and task boundaries
- acceptance criteria and stop conditions
- validation habits
- when to checkpoint or split sessions
- how to ask the next prompt

Do not suggest changing the agent's system prompt, hidden instructions, internal reasoning, \
or tool implementation.
"""


def build_coach_enhancement_prompt(metrics: SessionMetrics, report: CoachReport) -> str:
    lines = [
        SYSTEM_PROMPT,
        "",
        "Use this compact coding-agent session summary to provide contextual coaching.",
        "Return Markdown with these sections:",
        "1. Top 3 Habits To Improve",
        "2. Better Prompt Rewrite",
        "3. Suggested Next Prompt",
        "4. Model Tier Guidance",
        "5. Why This Session Took The Shape It Did",
        "",
        "Keep advice concrete and specific to the session. Do not invent file contents "
        "or vendor-specific model names.",
        "",
        "## Session Summary",
        f"- Agent: {metrics.session.agent_type}",
        f"- Model: {metrics.session.model}",
        f"- Project: {metrics.session.project_path}",
        f"- Turns: {len(metrics.turns)}",
        f"- Input tokens: {metrics.total_usage.input_tokens:,}",
        f"- Output tokens: {metrics.total_usage.output_tokens:,}",
        f"- Cache created: {metrics.total_usage.cache_creation_tokens:,}",
        f"- Cache read: {metrics.total_usage.cache_read_tokens:,}",
        f"- Estimated API-equivalent cost: ${metrics.total_cost:.3f}",
        f"- Local coach score: {report.score}/100",
        "",
    ]

    if report.model_recommendation is not None:
        recommendation = report.model_recommendation
        lines.extend(
            [
                "## Local Model Fit Recommendation",
                f"- Recommended tier: {recommendation.tier}",
                f"- Confidence: {recommendation.confidence}",
                f"- Detail: {recommendation.detail}",
                f"- Next step: {recommendation.next_step}",
                "- Reasons:",
                *[f"  - {reason}" for reason in recommendation.reasons],
            ]
        )
        if recommendation.escalation_triggers:
            lines.extend(
                [
                    "- Escalation triggers:",
                    *[
                        f"  - {trigger}"
                        for trigger in recommendation.escalation_triggers
                    ],
                ]
            )

    lines.extend(["", "## Tool Usage"])

    total_calls = sum(stat.calls for stat in metrics.tool_stats.values())
    if total_calls == 0:
        lines.append("- No tool calls recorded")
    else:
        for stat in sorted(metrics.tool_stats.values(), key=lambda item: -item.calls)[:8]:
            pct = stat.calls / total_calls * 100
            lines.append(f"- {stat.name}: {stat.calls} calls ({pct:.0f}%)")

    if metrics.alerts:
        lines.extend(["", "## Drift Alerts"])
        for alert in metrics.alerts[:8]:
            lines.append(f"- [{alert.severity}] {alert.type}: {alert.description}")

    user_turns = [turn for turn in metrics.turns if turn.role == "user"]
    if user_turns:
        lines.extend(["", "## User Prompts"])
        for turn in user_turns[-8:]:
            if turn.content_preview:
                lines.append(f"- Turn {turn.number}: {turn.content_preview[:220]}")

    assistant_turns = [turn for turn in metrics.turns if turn.role == "assistant"]
    if assistant_turns:
        lines.extend(["", "## Recent Agent Activity"])
        for turn in assistant_turns[-8:]:
            tool_names = ", ".join(tool.name for tool in turn.tool_calls) or "none"
            lines.append(
                f"- Turn {turn.number}: output={turn.usage.output_tokens}, "
                f"tools=[{tool_names}], preview={turn.content_preview[:140]}"
            )

    lines.extend(["", "## Local Coach Findings"])
    for finding in report.findings:
        lines.append(
            f"- [{finding.severity}] {finding.category}: {finding.title}. "
            f"{finding.detail}"
        )
        if finding.suggestion:
            lines.append(f"  Suggested local action: {finding.suggestion}")

    lines.extend(
        [
            "",
            "## Local Suggested Next Prompt",
            report.suggested_next_prompt,
        ]
    )

    return "\n".join(lines)
