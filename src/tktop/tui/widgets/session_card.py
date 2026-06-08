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
        indicator = "●" if s.status in ("idle", "busy") else "○"
        color = "green" if s.status == "busy" else "cyan" if s.status == "idle" else "dim"
        project = Path(s.project_path).name
        title = s.title or project

        text = Text()
        text.append(f" {indicator} ", style=color)
        text.append(f"{title[:40]:<42} ", style="bold")
        text.append(f"~/{project:<20} ", style="dim")
        text.append(f"{s.status}", style=color)
        return text

    def watch_selected(self, value: bool) -> None:
        self.set_class(value, "-selected")
