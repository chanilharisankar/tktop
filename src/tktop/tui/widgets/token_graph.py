from textual.widgets import Sparkline


class TokenGraph(Sparkline):
    def __init__(self, data: list[int] | None = None, **kwargs) -> None:
        super().__init__(data=[float(d) for d in (data or [])] or [0.0], **kwargs)

    def update_data(self, data: list[int]) -> None:
        self.data = [float(d) for d in data] or [0.0]
        self.refresh()
