from tktop.metrics.types import SessionMetrics

SYSTEM_PROMPT = """\
You are an expert at optimizing token usage for AI coding agents like Claude Code, \
Cursor, and Aider. You analyze session telemetry and provide actionable advice that \
developers can actually implement.

Key context:
- Claude Code is an autonomous coding agent that runs in the terminal
- The developer does NOT control the system prompt or agent internals
- The developer CAN control: their own prompts, CLAUDE.md files, project structure, \
which tasks they delegate to the agent, and when to start new sessions
- Cache tokens use Anthropic's prompt caching (5-minute TTL). Cache reads are 10x \
cheaper than fresh input. Cache writes happen when new context is added.
- Output tokens are the most expensive (5x input price for most models)
- Tool calls (Bash, Read, Edit, Write, WebFetch) consume tokens for both the call \
and the response

What developers CAN do to reduce costs:
- Write clearer, more specific prompts so the agent doesn't explore unnecessary paths
- Use CLAUDE.md to pre-document project context, reducing repeated discovery
- Break large tasks into smaller, focused requests
- Start new sessions when context grows too large (resets cache)
- Avoid vague instructions that cause the agent to read many files searching for context
- Use cheaper models (Sonnet vs Opus) for routine tasks

What developers CANNOT do (do NOT suggest these):
- Modify the agent's system prompt or internal instructions
- Add custom guardrails or stop sequences to the agent
- Change how the agent uses tools internally
- Modify the agent's reasoning or chain-of-thought behavior
"""


def build_analysis_prompt(metrics: SessionMetrics) -> str:
    lines = [
        "Analyze this coding agent session and suggest practical ways to reduce "
        "token usage and cost. Focus on what the developer can change about their "
        "workflow, not the agent's internals.",
        "",
        "## Session Data",
        f"- Agent: {metrics.session.agent_type}",
        f"- Model: {metrics.session.model}",
        f"- Total turns: {len(metrics.turns)}",
        f"- Input tokens: {metrics.total_usage.input_tokens:,}",
        f"- Output tokens: {metrics.total_usage.output_tokens:,}",
        f"- Cache created: {metrics.total_usage.cache_creation_tokens:,}",
        f"- Cache read: {metrics.total_usage.cache_read_tokens:,}",
        f"- Estimated cost: ${metrics.total_cost:.3f}",
    ]

    cache_total = (
        metrics.total_usage.cache_creation_tokens
        + metrics.total_usage.cache_read_tokens
    )
    if cache_total > 0:
        hit_ratio = metrics.total_usage.cache_read_tokens / cache_total * 100
        lines.append(f"- Cache hit ratio: {hit_ratio:.0f}%")

    lines.append("")
    lines.append("## Tool Usage")

    total_calls = sum(s.calls for s in metrics.tool_stats.values())
    for stat in sorted(metrics.tool_stats.values(), key=lambda s: -s.calls):
        pct = (stat.calls / total_calls * 100) if total_calls > 0 else 0
        lines.append(f"- {stat.name}: {stat.calls} calls ({pct:.0f}%)")

    if metrics.alerts:
        lines.append("")
        lines.append("## Detected Issues")
        for alert in metrics.alerts:
            lines.append(
                f"- [{alert.severity}] {alert.type}: {alert.description}"
            )

    assistant_turns = [t for t in metrics.turns if t.role == "assistant"]
    user_turns = [t for t in metrics.turns if t.role == "user"]

    if user_turns:
        lines.append("")
        lines.append("## User Prompts (what the developer asked)")
        for turn in user_turns[-5:]:
            if turn.content_preview:
                lines.append(f"- \"{turn.content_preview[:150]}\"")

    if assistant_turns:
        lines.append("")
        lines.append("## Agent Activity (last 10 turns)")
        for turn in assistant_turns[-10:]:
            tool_names = ", ".join(tc.name for tc in turn.tool_calls) or "none"
            lines.append(
                f"- Turn #{turn.number}: out={turn.usage.output_tokens} "
                f"tools=[{tool_names}] — {turn.content_preview[:100]}"
            )

    lines.extend([
        "",
        "## Instructions",
        "Provide 3-5 specific, actionable recommendations that the developer can "
        "implement in their next session. For each recommendation:",
        "- Explain what pattern you observed in the data",
        "- Explain why it costs tokens",
        "- Give a concrete action the developer can take",
        "",
        "Focus on practical workflow changes, not agent configuration.",
    ])

    return "\n".join(lines)
