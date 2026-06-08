from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Footer, Header, Static

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
        yield Header()
        yield Static(f" Turn #{self.turn.number} — {self.turn.role} — stub")
        yield Footer()

    def action_go_back(self) -> None:
        self.app.pop_screen()

    def action_quit(self) -> None:
        self.app.exit()
