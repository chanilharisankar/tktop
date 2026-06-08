from pathlib import Path

from rich.text import Text
from textual.reactive import reactive
from textual.widgets import Static

from tktop.metrics.types import SessionInfo


class SessionCard(Static):
    selected = reactive(False)

    def __init__(self, session: SessionInfo, **kwargs) -> None:
        super().__init__(**kwargs)
        self.session = session

    def render(self) -> Text:
        s = self.session
        indicator = "●" if s.status == "idle" else "○"
        color = "green" if s.status == "idle" else "dim"
        project = Path(s.project_path).name

        text = Text()
        text.append(f" {indicator} ", style=color)
        text.append(f"{s.agent_type:<14} ", style="bold")
        text.append(f"~/{project:<26} ", style="white")
        text.append(f"pid:{s.pid:<8} ", style="dim")
        text.append(f"{s.status}", style=color)
        return text

    def watch_selected(self, value: bool) -> None:
        self.set_class(value, "-selected")
