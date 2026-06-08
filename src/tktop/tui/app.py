from textual import on
from textual.app import App
from textual.binding import Binding

from tktop.adapter.claude import ClaudeCodeAdapter
from tktop.config import Config, load_config
from tktop.tui.screens.overview import OverviewScreen, SessionSelected


class TktopApp(App):
    CSS_PATH = "styles.tcss"
    TITLE = "tktop"
    SUB_TITLE = "token monitor for coding agents"

    BINDINGS = [
        Binding("q", "quit", "Quit"),
    ]

    def __init__(self, config: Config | None = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self.config = config or load_config()
        self.adapter = ClaudeCodeAdapter(self.config.claude_dir)

    def on_mount(self) -> None:
        self.push_screen(OverviewScreen(self.adapter))

    @on(SessionSelected)
    def on_session_selected(self, message: SessionSelected) -> None:
        from tktop.tui.screens.dashboard import DashboardScreen

        self.push_screen(DashboardScreen(message.session, self.adapter, self.config))
