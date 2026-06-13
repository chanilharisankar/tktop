from tktop.metrics.pricing import calculate_cost, calculate_cost_breakdown
from tktop.metrics.types import (
    SessionInfo,
    SessionMetrics,
    TokenUsage,
    ToolStat,
    Turn,
    TurnCost,
)


def aggregate(session: SessionInfo, turns: list[Turn]) -> SessionMetrics:
    total_usage = TokenUsage()
    tool_stats: dict[str, ToolStat] = {}
    tokens_per_turn: list[int] = []
    cost_per_turn: list[float] = []
    turn_costs: list[TurnCost] = []
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

        cumulative_cost = calculate_cost(model, total_usage)
        cost_per_turn.append(cumulative_cost)

        inp, out, cw, cr = calculate_cost_breakdown(model, turn.usage)
        turn_costs.append(TurnCost(
            turn_number=turn.number,
            input_cost=inp,
            output_cost=out,
            cache_write_cost=cw,
            cache_read_cost=cr,
        ))

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
        cost_per_turn=cost_per_turn,
        turn_costs=turn_costs,
    )
