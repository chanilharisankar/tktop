from rich.text import Text
from textual.widgets import Static

from tktop.metrics.types import TokenUsage


class TokenBars(Static):
    def __init__(self, usage: TokenUsage | None = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self.usage = usage or TokenUsage()

    def render(self) -> Text:
        total = self.usage.total
        text = Text()

        bars = [
            ("Input      ", self.usage.input_tokens, "blue"),
            ("Cache Write", self.usage.cache_creation_tokens, "yellow"),
            ("Cache Read ", self.usage.cache_read_tokens, "green"),
            ("Output     ", self.usage.output_tokens, "magenta"),
        ]

        for label, value, color in bars:
            width = 30
            filled = (value * width // total) if total > 0 else 0
            filled = min(filled, width)
            pct = (value / total * 100) if total > 0 else 0

            text.append(f" {label} ", style="dim")
            text.append("█" * filled, style=color)
            text.append("░" * (width - filled), style="dim")
            text.append(f" {_fmt(value)} ", style=f"bold {color}")
            text.append(f"({pct:.0f}%)\n", style="dim")

        billable = self.usage.billable
        text.append("\n In+Out: ", style="dim")
        text.append(f"{_fmt(billable)} tokens", style="bold green")
        text.append("  All: ", style="dim")
        text.append(f"{_fmt(total)} tokens", style="dim")
        return text

    def update_usage(self, usage: TokenUsage) -> None:
        self.usage = usage
        self.refresh()


def _fmt(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}k"
    return str(n)
