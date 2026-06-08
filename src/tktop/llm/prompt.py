from tktop.metrics.types import SessionMetrics


def build_analysis_prompt(metrics: SessionMetrics) -> str:
    lines = [
        "You are an LLM token usage optimizer. Analyze this coding agent session "
        "and suggest specific ways to reduce token consumption.",
        "",
        "## Session Summary",
        f"- Agent: {metrics.session.agent_type}",
        f"- Model: {metrics.session.model}",
        f"- Total turns: {len(metrics.turns)}",
        f"- Input tokens: {metrics.total_usage.input_tokens:,}",
        f"- Output tokens: {metrics.total_usage.output_tokens:,}",
        f"- Cache created: {metrics.total_usage.cache_creation_tokens:,}",
        f"- Cache read: {metrics.total_usage.cache_read_tokens:,}",
        f"- Estimated cost: ${metrics.total_cost:.3f}",
        "",
        "## Tool Usage",
    ]

    total_calls = sum(s.calls for s in metrics.tool_stats.values())
    for stat in sorted(metrics.tool_stats.values(), key=lambda s: -s.calls):
        pct = (stat.calls / total_calls * 100) if total_calls > 0 else 0
        lines.append(f"- {stat.name}: {stat.calls} calls ({pct:.0f}%)")

    if metrics.alerts:
        lines.append("")
        lines.append("## Detected Issues")
        for alert in metrics.alerts:
            lines.append(f"- [{alert.severity}] {alert.type}: {alert.description}")

    assistant_turns = [t for t in metrics.turns if t.role == "assistant"]
    if assistant_turns:
        lines.append("")
        lines.append("## Recent Conversation Samples")
        for turn in assistant_turns[-10:]:
            tool_names = ", ".join(tc.name for tc in turn.tool_calls) or "none"
            lines.append(
                f"- Turn #{turn.number}: out={turn.usage.output_tokens} "
                f"tools=[{tool_names}] — {turn.content_preview[:100]}"
            )

    lines.extend([
        "",
        "## Instructions",
        "Provide 3-5 specific, actionable recommendations. Categorize each as:",
        "1. **Input Optimization** — reducing prompt/context tokens",
        "2. **Guardrail Advice** — preventing drift and loops",
        "3. **Tool Pruning** — reducing tool call overhead",
        "",
        "Be specific. Reference actual numbers from the data above.",
    ])

    return "\n".join(lines)
