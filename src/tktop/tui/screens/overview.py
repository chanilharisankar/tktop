from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Footer, Header, Static

from tktop.adapter.protocol import SessionAdapter


class OverviewScreen(Screen):
    BINDINGS = [
        Binding("q", "quit", "Quit"),
    ]

    def __init__(self, adapter: SessionAdapter, **kwargs) -> None:
        super().__init__(**kwargs)
        self.adapter = adapter

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static(" tktop — loading sessions...")
        yield Footer()

    def action_quit(self) -> None:
        self.app.exit()
