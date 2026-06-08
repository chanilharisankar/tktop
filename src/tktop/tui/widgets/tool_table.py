from rich.table import Table
from textual.widgets import Static

from tktop.metrics.types import ToolStat


class ToolTable(Static):
    def __init__(self, tool_stats: dict[str, ToolStat] | None = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self.tool_stats = tool_stats or {}

    def render(self) -> Table:
        table = Table(show_header=True, expand=True, box=None)
        table.add_column("Tool", style="bold", width=14)
        table.add_column("Calls", justify="right", width=8)
        table.add_column("Turns", justify="right", width=8)
        table.add_column("", width=15)

        sorted_stats = sorted(
            self.tool_stats.values(), key=lambda s: s.calls, reverse=True
        )
        max_calls = sorted_stats[0].calls if sorted_stats else 1

        for stat in sorted_stats[:8]:
            bar_len = max(1, stat.calls * 10 // max_calls)
            bar = "█" * bar_len
            table.add_row(stat.name, str(stat.calls), str(stat.turns_present), f"[cyan]{bar}")

        return table

    def update_stats(self, tool_stats: dict[str, ToolStat]) -> None:
        self.tool_stats = tool_stats
        self.refresh()
