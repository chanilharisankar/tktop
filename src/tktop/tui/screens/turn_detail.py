from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Footer, Header, Static

from tktop.metrics.pricing import calculate_cost
from tktop.metrics.types import Turn


class TurnDetailScreen(Screen):
    BINDINGS = [
        Binding("escape", "go_back", "Back"),
        Binding("q", "quit", "Quit"),
    ]

    def __init__(self, turn: Turn, **kwargs) -> None:
        super().__init__(**kwargs)
        self.turn = turn

    def compose(self) -> ComposeResult:
        t = self.turn
        model = t.model or "unknown"
        cost = calculate_cost(model, t.usage)

        yield Header()
        yield VerticalScroll(
            Horizontal(
                Vertical(
                    Static(" TOKEN USAGE", classes="panel-title"),
                    Static(
                        f" Input tokens:     {t.usage.input_tokens:>10,}\n"
                        f" Output tokens:    {t.usage.output_tokens:>10,}\n"
                        f" Cache write:      {t.usage.cache_creation_tokens:>10,}\n"
                        f" Cache read:       {t.usage.cache_read_tokens:>10,}\n"
                        f" Estimated API-equivalent cost this turn: ${cost:>9.4f}"
                    ),
                    classes="panel",
                ),
                Vertical(
                    Static(" TOOL CALLS", classes="panel-title"),
                    Static(
                        "\n".join(
                            f" {i + 1}. {tc.name}  ({tc.id[:20]}...)"
                            for i, tc in enumerate(t.tool_calls)
                        )
                        or " No tool calls"
                    ),
                    classes="panel",
                ),
            ),
            Vertical(
                Static(" CONTENT PREVIEW", classes="panel-title"),
                Static(
                    f" {t.content_preview}" if t.content_preview else " (no text content)"
                ),
                classes="panel",
            ),
        )
        yield Footer()

        self.sub_title = (
            f"Turn #{t.number} — {t.role} — "
            f"{t.timestamp.strftime('%H:%M:%S')} — {model}"
        )

    def action_go_back(self) -> None:
        self.app.pop_screen()

    def action_quit(self) -> None:
        self.app.exit()
