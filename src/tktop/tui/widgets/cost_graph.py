from __future__ import annotations

from rich.text import Text
from textual.widgets import Static

from tktop.metrics.types import TurnCost


class CostGraph(Static):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.data: list[float] = []
        self.turn_costs: list[TurnCost] = []
        self.total_cost: float = 0.0
        self.turn_count: int = 0

    def render(self) -> Text:
        text = Text()

        text.append(" Total ", style="dim")
        text.append(f"${self.total_cost:.4f}", style="bold green")
        text.append("  Turns ", style="dim")
        text.append(str(self.turn_count), style="bold")
        text.append("\n\n")

        if len(self.data) < 2:
            text.append(" Waiting for data...", style="dim")
            return text

        height = 6
        width = min(len(self.data), 60)
        sampled = _sample(self.data, width)

        max_val = max(sampled) if sampled else 1.0
        min_val = min(sampled) if sampled else 0.0
        val_range = max_val - min_val or max_val or 1.0

        blocks = " ▁▂▃▄▅▆▇█"

        for row in range(height - 1, -1, -1):
            row_low = min_val + val_range * row / height
            row_high = min_val + val_range * (row + 1) / height
            text.append(" ", style="dim")
            if row == height - 1:
                text.append(f"${max_val:<7.4f} ", style="dim")
            elif row == 0:
                text.append(f"${min_val:<7.4f} ", style="dim")
            else:
                text.append("         ", style="dim")

            for val in sampled:
                if val >= row_high:
                    text.append("█", style="green")
                elif val > row_low:
                    frac = (val - row_low) / (row_high - row_low)
                    idx = int(frac * (len(blocks) - 1))
                    text.append(blocks[idx], style="green")
                else:
                    text.append(" ")
            text.append("\n")

        text.append("          ", style="dim")
        text.append("└" + "─" * len(sampled), style="dim")
        text.append(" turns", style="dim")

        if self.turn_costs:
            text.append("\n\n")
            _render_breakdown_table(text, self.turn_costs)

        return text

    def update_data(
        self,
        data: list[float],
        total_cost: float,
        turn_count: int,
        turn_costs: list[TurnCost] | None = None,
    ) -> None:
        self.data = data
        self.total_cost = total_cost
        self.turn_count = turn_count
        self.turn_costs = turn_costs or []
        self.refresh()


def _render_breakdown_table(text: Text, turn_costs: list[TurnCost]) -> None:
    visible = turn_costs[-10:]

    text.append(" #   ", style="bold dim")
    text.append("Input   ", style="bold blue")
    text.append("Output  ", style="bold magenta")
    text.append("CaWr    ", style="bold yellow")
    text.append("CaRd    ", style="bold green")
    text.append("Total\n", style="bold")

    for tc in visible:
        text.append(f" {tc.turn_number:<4}", style="dim")
        text.append(f"{_cost(tc.input_cost):<8}", style="blue")
        text.append(f"{_cost(tc.output_cost):<8}", style="magenta")
        text.append(f"{_cost(tc.cache_write_cost):<8}", style="yellow")
        text.append(f"{_cost(tc.cache_read_cost):<8}", style="green")
        text.append(f"{_cost(tc.total)}\n", style="bold")

    if len(turn_costs) > 10:
        text.append(f" ... {len(turn_costs) - 10} earlier turns hidden\n", style="dim")


def _cost(v: float) -> str:
    if v == 0:
        return "—"
    if v < 0.001:
        return f"${v:.5f}"
    return f"${v:.4f}"


def _sample(data: list[float], width: int) -> list[float]:
    if len(data) <= width:
        return data
    step = len(data) / width
    return [data[int(i * step)] for i in range(width)]
