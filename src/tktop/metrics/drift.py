from datetime import UTC, datetime

from tktop.metrics.types import Alert, Turn


def detect_drift(turns: list[Turn]) -> list[Alert]:
    alerts: list[Alert] = []
    alerts.extend(_detect_tool_loop(turns))
    alerts.extend(_detect_read_loop(turns))
    alerts.extend(_detect_edit_thrash(turns))
    alerts.extend(_detect_permission_loop(turns))
    alerts.extend(_detect_token_explosion(turns))
    alerts.extend(_detect_runaway(turns))
    alerts.extend(_detect_cache_miss_streak(turns))
    alerts.extend(_detect_cost_spike(turns))
    return _dedupe(alerts)


def _detect_tool_loop(turns: list[Turn]) -> list[Alert]:
    alerts: list[Alert] = []
    assistant_run: list[Turn] = []

    for turn in turns:
        if turn.role == "assistant":
            assistant_run.append(turn)
        else:
            assistant_run = []

        if len(assistant_run) < 3:
            continue

        window = assistant_run[-5:]
        tool_counts: dict[str, int] = {}
        for t in window:
            for tc in t.tool_calls:
                tool_counts[tc.name] = tool_counts.get(tc.name, 0) + 1

        for tool_name, count in tool_counts.items():
            if count >= 3:
                alerts.append(
                    Alert(
                        severity="warning",
                        type="tool_loop",
                        description=(
                            f"{tool_name} called {count}x "
                            f"in last {len(window)} consecutive turns"
                        ),
                        detected_at=datetime.now(tz=UTC),
                    )
                )

    return alerts


def _detect_read_loop(turns: list[Turn]) -> list[Alert]:
    read_count = 0
    for turn in turns:
        if turn.role != "assistant":
            continue
        for tc in turn.tool_calls:
            if tc.name == "Read":
                read_count += 1

    if read_count >= 4:
        return [
            Alert(
                severity="warning",
                type="read_loop",
                description=f"Read tool called {read_count}x in this session",
                detected_at=datetime.now(tz=UTC),
            )
        ]
    return []


def _detect_edit_thrash(turns: list[Turn]) -> list[Alert]:
    window_size = 10
    assistant_turns = [t for t in turns if t.role == "assistant"]

    for i in range(len(assistant_turns)):
        window = assistant_turns[max(0, i - window_size + 1) : i + 1]
        edit_count = 0
        for t in window:
            for tc in t.tool_calls:
                if tc.name in ("Edit", "Write"):
                    edit_count += 1

        if edit_count >= 5:
            return [
                Alert(
                    severity="critical",
                    type="edit_thrash",
                    description=(
                        f"Edit/Write called {edit_count}x in last "
                        f"{len(window)} turns — possible thrashing"
                    ),
                    detected_at=datetime.now(tz=UTC),
                )
            ]

    return []


def _detect_permission_loop(turns: list[Turn]) -> list[Alert]:
    pattern_count = 0
    last_tool: str | None = None

    for turn in turns:
        if turn.role == "assistant" and turn.tool_calls:
            tool_name = turn.tool_calls[0].name
            if tool_name == last_tool:
                pattern_count += 1
            else:
                pattern_count = 1
                last_tool = tool_name
        elif turn.role == "user":
            continue
        else:
            pattern_count = 0
            last_tool = None

    if pattern_count >= 3 and last_tool:
        return [
            Alert(
                severity="warning",
                type="permission_loop",
                description=(
                    f"{last_tool} attempted {pattern_count}x with user "
                    f"responses between — possible permission denial loop"
                ),
                detected_at=datetime.now(tz=UTC),
            )
        ]

    return []


def _detect_token_explosion(turns: list[Turn]) -> list[Alert]:
    assistant_outputs: list[int] = []

    for turn in turns:
        if turn.role != "assistant":
            continue
        assistant_outputs.append(turn.usage.output_tokens)

        if len(assistant_outputs) < 3:
            continue

        last3 = assistant_outputs[-3:]
        if last3[0] > 0 and last3[1] > last3[0] * 2 and last3[2] > last3[1] * 2:
            return [
                Alert(
                    severity="warning",
                    type="token_explosion",
                    description="output tokens doubling each turn",
                    detected_at=datetime.now(tz=UTC),
                )
            ]

    return []


def _detect_runaway(turns: list[Turn]) -> list[Alert]:
    trailing_assistant = 0
    trailing_output = 0

    for turn in reversed(turns):
        if turn.role == "user":
            break
        if turn.role == "assistant":
            trailing_assistant += 1
            trailing_output += turn.usage.output_tokens

    if trailing_assistant >= 10 and trailing_output > 500_000:
        return [
            Alert(
                severity="critical",
                type="runaway",
                description=(
                    f"no user interaction in last {trailing_assistant} turns, "
                    f"{trailing_output:,} output tokens"
                ),
                detected_at=datetime.now(tz=UTC),
            )
        ]

    return []


def _detect_cache_miss_streak(turns: list[Turn]) -> list[Alert]:
    streak = 0

    for turn in turns:
        if turn.role != "assistant":
            continue
        if turn.usage.cache_read_tokens == 0 and turn.usage.cache_creation_tokens > 0:
            streak += 1
        else:
            streak = 0

        if streak >= 5:
            return [
                Alert(
                    severity="warning",
                    type="cache_miss_streak",
                    description=(
                        f"cache not reused for {streak} consecutive turns "
                        f"despite cache creation"
                    ),
                    detected_at=datetime.now(tz=UTC),
                )
            ]

    return []


def _detect_cost_spike(turns: list[Turn]) -> list[Alert]:
    from tktop.metrics.pricing import calculate_cost

    assistant_turns = [t for t in turns if t.role == "assistant"]
    if len(assistant_turns) < 3:
        return []

    costs = []
    for t in assistant_turns:
        model = t.model or "claude-sonnet-4-6"
        costs.append(calculate_cost(model, t.usage))

    avg_cost = sum(costs) / len(costs)
    if avg_cost == 0:
        return []

    alerts: list[Alert] = []
    for i, cost in enumerate(costs):
        if cost > avg_cost * 2:
            alerts.append(
                Alert(
                    severity="info",
                    type="cost_spike",
                    description=(
                        f"turn #{assistant_turns[i].number} cost ${cost:.4f} "
                        f"(avg ${avg_cost:.4f})"
                    ),
                    detected_at=datetime.now(tz=UTC),
                )
            )

    return alerts


def _dedupe(alerts: list[Alert]) -> list[Alert]:
    seen: set[str] = set()
    result: list[Alert] = []
    for alert in alerts:
        key = f"{alert.type}:{alert.description}"
        if key not in seen:
            seen.add(key)
            result.append(alert)
    return result
