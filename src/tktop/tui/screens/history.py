from collections import defaultdict
from datetime import datetime, timedelta, timezone

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header, Static

from tktop.adapter.protocol import SessionAdapter
from tktop.metrics.pricing import calculate_cost
from tktop.metrics.types import TokenUsage

UTC = timezone.utc


class DailyStats:
    def __init__(self) -> None:
        self.sessions: set[str] = set()
        self.turns = 0
        self.usage = TokenUsage()
        self.cost = 0.0


class HistoryScreen(Screen):
    BINDINGS = [
        Binding("escape", "go_back", "Back"),
        Binding("r", "refresh", "Refresh"),
        Binding("q", "quit", "Quit"),
    ]

    def __init__(self, adapter: SessionAdapter, **kwargs) -> None:
        super().__init__(**kwargs)
        self.adapter = adapter

    def compose(self) -> ComposeResult:
        yield Header()
        yield VerticalScroll(
            Vertical(
                Static(" DAILY USAGE HISTORY (last 7 days)", classes="panel-title"),
                DataTable(id="history-table"),
                classes="panel",
            ),
            Vertical(
                Static(" DAILY COST", classes="panel-title"),
                Static("", id="cost-bars"),
                classes="panel",
            ),
        )
        yield Footer()
        self.sub_title = "Daily Usage History"

    def on_mount(self) -> None:
        table = self.query_one("#history-table", DataTable)
        table.cursor_type = "row"
        table.add_columns(
            "Date", "Sessions", "Turns", "Input", "Output", "Cache", "Cost"
        )
        self.load_history()

    @work
    async def load_history(self) -> None:
        sessions = await self.adapter.discover()
        now = datetime.now(tz=UTC)
        cutoff = now - timedelta(days=7)

        daily: dict[str, DailyStats] = defaultdict(DailyStats)

        for session in sessions:
            turns = await self.adapter.parse_transcript(session.id)
            if not turns:
                continue

            for turn in turns:
                if turn.role != "assistant":
                    continue
                if turn.timestamp < cutoff:
                    continue

                day_key = turn.timestamp.strftime("%Y-%m-%d")
                stats = daily[day_key]
                stats.sessions.add(session.id)
                stats.turns += 1
                stats.usage.input_tokens += turn.usage.input_tokens
                stats.usage.output_tokens += turn.usage.output_tokens
                stats.usage.cache_creation_tokens += turn.usage.cache_creation_tokens
                stats.usage.cache_read_tokens += turn.usage.cache_read_tokens

                model = turn.model or session.model or "unknown"
                stats.cost += calculate_cost(model, turn.usage)

        table = self.query_one("#history-table", DataTable)
        table.clear()

        sorted_days = sorted(daily.keys(), reverse=True)
        total = DailyStats()
        cost_data: list[float] = []

        for day in sorted_days:
            s = daily[day]
            table.add_row(
                day,
                str(len(s.sessions)),
                str(s.turns),
                _fmt(s.usage.input_tokens),
                _fmt(s.usage.output_tokens),
                _fmt(s.usage.cache_read_tokens),
                f"${s.cost:.2f}",
            )
            total.sessions.update(s.sessions)
            total.turns += s.turns
            total.usage.input_tokens += s.usage.input_tokens
            total.usage.output_tokens += s.usage.output_tokens
            total.usage.cache_read_tokens += s.usage.cache_read_tokens
            total.cost += s.cost
            cost_data.append(s.cost)

        if sorted_days:
            table.add_row(
                "─ Total ─",
                str(len(total.sessions)),
                str(total.turns),
                _fmt(total.usage.input_tokens),
                _fmt(total.usage.output_tokens),
                _fmt(total.usage.cache_read_tokens),
                f"${total.cost:.2f}",
            )

        cost_bars = self.query_one("#cost-bars", Static)
        cost_bars.update(_build_cost_bars(sorted_days, daily))

    def action_go_back(self) -> None:
        self.app.pop_screen()

    def action_refresh(self) -> None:
        self.load_history()

    def action_quit(self) -> None:
        self.app.exit()


def _build_cost_bars(
    sorted_days: list[str], daily: dict[str, DailyStats]
) -> str:
    if not sorted_days:
        return " No data"

    max_cost = max(daily[d].cost for d in sorted_days)
    if max_cost == 0:
        return " No costs recorded"

    bar_width = 30
    lines: list[str] = []

    for day in reversed(sorted_days):
        cost = daily[day].cost
        filled = int(cost / max_cost * bar_width)
        filled = max(1, filled) if cost > 0 else 0

        bar = "█" * filled + "░" * (bar_width - filled)
        label = datetime.strptime(day, "%Y-%m-%d").strftime("%b %d")

        marker = " ◀" if cost == max_cost else ""
        lines.append(f" {label}  ${cost:>7.2f}  {bar}{marker}")

    return "\n".join(lines)


def _fmt(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}k"
    return str(n)
