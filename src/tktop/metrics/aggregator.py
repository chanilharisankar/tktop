from tktop.metrics.pricing import calculate_cost
from tktop.metrics.types import (
    SessionInfo,
    SessionMetrics,
    TokenUsage,
    ToolStat,
    Turn,
)


def aggregate(session: SessionInfo, turns: list[Turn]) -> SessionMetrics:
    total_usage = TokenUsage()
    tool_stats: dict[str, ToolStat] = {}
    tokens_per_turn: list[int] = []
    model = session.model

    for turn in turns:
        if turn.role != "assistant":
            continue

        total_usage.input_tokens += turn.usage.input_tokens
        total_usage.output_tokens += turn.usage.output_tokens
        total_usage.cache_creation_tokens += turn.usage.cache_creation_tokens
        total_usage.cache_read_tokens += turn.usage.cache_read_tokens

        tokens_per_turn.append(turn.usage.output_tokens)

        if turn.model:
            model = turn.model

        tools_in_turn: set[str] = set()
        for tc in turn.tool_calls:
            if tc.name not in tool_stats:
                tool_stats[tc.name] = ToolStat(name=tc.name)
            tool_stats[tc.name].calls += 1
            tools_in_turn.add(tc.name)

        for tool_name in tools_in_turn:
            tool_stats[tool_name].turns_present += 1

    total_cost = calculate_cost(model, total_usage)

    return SessionMetrics(
        session=session,
        turns=turns,
        total_usage=total_usage,
        total_cost=total_cost,
        tool_stats=tool_stats,
        tokens_per_turn=tokens_per_turn,
    )
