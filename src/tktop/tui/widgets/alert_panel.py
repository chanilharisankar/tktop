from rich.text import Text
from textual.widgets import Static

from tktop.metrics.types import Alert


class AlertPanel(Static):
    def __init__(self, alerts: list[Alert] | None = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self.alerts = alerts or []

    def render(self) -> Text:
        text = Text()

        if not self.alerts:
            text.append(" No issues detected", style="dim")
            return text

        for alert in self.alerts:
            if alert.severity == "critical":
                text.append(" ✖ ", style="bold red")
            elif alert.severity == "warning":
                text.append(" ⚠ ", style="bold yellow")
            else:
                text.append(" ℹ ", style="bold blue")
            text.append(f"{alert.description}\n")

        return text

    def update_alerts(self, alerts: list[Alert]) -> None:
        self.alerts = alerts
        self.refresh()
