from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Footer, Header, Static

from tktop.adapter.protocol import SessionAdapter
from tktop.config import Config
from tktop.metrics.types import SessionInfo


class DashboardScreen(Screen):
    BINDINGS = [
        Binding("escape", "go_back", "Back"),
        Binding("q", "quit", "Quit"),
    ]

    def __init__(self, session: SessionInfo, adapter: SessionAdapter, config: Config, **kwargs) -> None:
        super().__init__(**kwargs)
        self.session = session
        self.adapter = adapter
        self.config = config

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static(f" Dashboard — {self.session.project_path} (loading...)")
        yield Footer()

    def action_go_back(self) -> None:
        self.app.pop_screen()

    def action_quit(self) -> None:
        self.app.exit()
