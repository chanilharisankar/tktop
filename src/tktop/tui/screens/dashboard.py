from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header, Static

from tktop.adapter.protocol import SessionAdapter
from tktop.config import Config
from tktop.metrics.aggregator import aggregate
from tktop.metrics.drift import detect_drift
from tktop.metrics.types import SessionInfo, SessionMetrics
from tktop.tui.widgets.alert_panel import AlertPanel
from tktop.tui.widgets.token_bars import TokenBars
from tktop.tui.widgets.token_graph import TokenGraph
from tktop.tui.widgets.tool_table import ToolTable


class DashboardScreen(Screen):
    BINDINGS = [
        Binding("escape", "go_back", "Back"),
        Binding("q", "quit", "Quit"),
        Binding("a", "analyze", "Analyze"),
        Binding("r", "refresh", "Refresh"),
    ]

    def __init__(
        self, session: SessionInfo, adapter: SessionAdapter, config: Config, **kwargs
    ) -> None:
        super().__init__(**kwargs)
        self.session = session
        self.adapter = adapter
        self.config = config
        self.metrics: SessionMetrics | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        scroll_children = [
            Horizontal(
                Vertical(
                    Static(" TOKEN USAGE", classes="panel-title"),
                    TokenBars(id="token-bars"),
                    classes="panel",
                ),
                Vertical(
                    Static(" COST", classes="panel-title"),
                    Static(" Loading...", id="cost-panel"),
                    classes="panel",
                ),
            ),
        ]
        if self.config.show_token_flow:
            scroll_children.append(
                Vertical(
                    Static(" TOKEN FLOW (output tokens per turn)", classes="panel-title"),
                    TokenGraph(id="token-graph"),
                    classes="panel",
                )
            )
        scroll_children.extend([
            Horizontal(
                Vertical(
                    Static(" TOOLS", classes="panel-title"),
                    ToolTable(id="tool-table"),
                    classes="panel",
                ),
                Vertical(
                    Static(" ALERTS", classes="panel-title"),
                    AlertPanel(id="alert-panel"),
                    classes="panel",
                ),
            ),
            Vertical(
                Static(" TURNS", classes="panel-title"),
                DataTable(id="turns-table"),
                classes="panel",
            ),
        ])
        yield VerticalScroll(*scroll_children)
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#turns-table", DataTable)
        table.add_columns("#", "Time", "Role", "Tokens", "Tools", "What")
        table.cursor_type = "row"
        self._last_turn_count = 0
        self.load_data()
        self.set_interval(2, self._auto_refresh)

    def _auto_refresh(self) -> None:
        self._refresh_data()

    @work
    async def load_data(self) -> None:
        turns = await self.adapter.parse_transcript(self.session.id)
        metrics = aggregate(self.session, turns)
        metrics.alerts = detect_drift(turns)
        self.metrics = metrics
        self._last_turn_count = 0
        self._update_panels(metrics)

    @work
    async def _refresh_data(self) -> None:
        turns = await self.adapter.parse_transcript(self.session.id)
        metrics = aggregate(self.session, turns)
        metrics.alerts = detect_drift(turns)
        self.metrics = metrics
        self._update_panels(metrics)

    def _update_panels(self, m: SessionMetrics) -> None:
        self.query_one("#token-bars", TokenBars).update_usage(m.total_usage)
        self.query_one("#tool-table", ToolTable).update_stats(m.tool_stats)
        self.query_one("#alert-panel", AlertPanel).update_alerts(m.alerts)
        if self.config.show_token_flow:
            self.query_one("#token-graph", TokenGraph).update_data(m.tokens_per_turn)

        model = self.session.model or "claude-sonnet-4-6"
        for turn in reversed(m.turns):
            if turn.model:
                model = turn.model
                break

        cost_text = (
            f" Model:       {model}\n"
            f" Total cost:  ${m.total_cost:.4f}\n"
            f" Turns:       {len(m.turns)}"
        )
        self.query_one("#cost-panel", Static).update(cost_text)

        table = self.query_one("#turns-table", DataTable)
        current_count = len(m.turns)

        if self._last_turn_count == 0:
            table.clear()
            for turn in m.turns[-50:]:
                self._add_turn_row(table, turn)
        elif current_count > self._last_turn_count:
            new_turns = m.turns[self._last_turn_count:]
            for turn in new_turns:
                self._add_turn_row(table, turn)
            table.move_cursor(row=table.row_count - 1)

        self._last_turn_count = current_count

        self.sub_title = (
            f"{self.session.project_path} — {model} — ${m.total_cost:.2f}"
        )

    def _add_turn_row(self, table: DataTable, turn) -> None:
        tools = ", ".join(tc.name for tc in turn.tool_calls) or "—"
        preview = turn.content_preview[:100].replace("\n", " ").strip()
        total = turn.usage.output_tokens + turn.usage.input_tokens
        tokens = f"{total:,}" if total else "—"
        table.add_row(
            str(turn.number),
            turn.timestamp.strftime("%H:%M:%S"),
            turn.role,
            tokens,
            tools,
            preview or "—",
            key=str(turn.number),
        )

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        if self.metrics is None:
            return
        turn_number = int(str(event.row_key.value))
        for turn in self.metrics.turns:
            if turn.number == turn_number:
                from tktop.tui.screens.turn_detail import TurnDetailScreen

                self.app.push_screen(TurnDetailScreen(turn))
                break

    def action_go_back(self) -> None:
        self.app.pop_screen()

    def action_quit(self) -> None:
        self.app.exit()

    def action_analyze(self) -> None:
        if self.metrics:
            from tktop.tui.screens.analysis import AnalysisScreen

            self.app.push_screen(AnalysisScreen(self.metrics, self.config))

    def action_refresh(self) -> None:
        self.load_data()
