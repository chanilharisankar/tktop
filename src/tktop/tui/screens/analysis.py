from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Footer, Header, Static

from tktop.config import Config
from tktop.metrics.types import SessionMetrics


class AnalysisScreen(Screen):
    BINDINGS = [
        Binding("escape", "go_back", "Back"),
        Binding("q", "quit", "Quit"),
    ]

    def __init__(self, metrics: SessionMetrics, config: Config, **kwargs) -> None:
        super().__init__(**kwargs)
        self.metrics = metrics
        self.config = config

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static(" Analysis — stub")
        yield Footer()

    def action_go_back(self) -> None:
        self.app.pop_screen()

    def action_quit(self) -> None:
        self.app.exit()
