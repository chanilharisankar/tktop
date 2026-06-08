from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.screen import Screen
from textual.widgets import Footer, Header, Markdown, Static

from tktop.config import Config
from tktop.llm.factory import create_provider
from tktop.llm.prompt import build_analysis_prompt
from tktop.metrics.types import SessionMetrics


class AnalysisScreen(Screen):
    BINDINGS = [
        Binding("escape", "go_back", "Back"),
        Binding("q", "quit", "Quit"),
    ]

    def __init__(self, metrics: SessionMetrics, config: Config, **kwargs) -> None:
        super().__init__(**kwargs)
        self.metrics = metrics
        self.config = config

    def compose(self) -> ComposeResult:
        m = self.metrics
        summary = (
            f" {len(m.turns)} turns • "
            f"{m.total_usage.billable:,} tokens (in+out) • "
            f"${m.total_cost:.2f} • "
            f"{len(m.tool_stats)} tools • "
            f"{len(m.alerts)} alerts"
        )

        yield Header()
        yield Static(f" SESSION: {summary}", id="analysis-summary")
        yield Static(" OPTIMIZATION RECOMMENDATIONS", classes="panel-title")
        yield VerticalScroll(
            Markdown("*Analyzing...*", id="analysis-result"),
            id="analysis-scroll",
        )
        yield Footer()

        self.sub_title = (
            f"Analysis — {m.session.project_path} — "
            f"powered by {self.config.llm_provider}/{self._model_name()}"
        )

    def _model_name(self) -> str:
        match self.config.llm_provider:
            case "ollama":
                return self.config.ollama_model
            case "anthropic":
                return self.config.anthropic_model
            case "vertex":
                return self.config.vertex_model
            case "openai":
                return self.config.openai_model
            case _:
                return "unknown"

    def on_mount(self) -> None:
        self.run_analysis()

    @work
    async def run_analysis(self) -> None:
        result_widget = self.query_one("#analysis-result", Markdown)
        provider = create_provider(self.config)

        if provider is None:
            await result_widget.update(
                f"**Error:** unknown LLM provider `{self.config.llm_provider}`"
            )
            return

        healthy = await provider.health_check()
        if not healthy:
            await result_widget.update(
                f"**Error:** `{provider.name}` is not reachable. "
                f"Check your configuration."
            )
            return

        prompt = build_analysis_prompt(self.metrics)
        try:
            result = await provider.analyze(prompt)
            await result_widget.update(result)
        except Exception as e:
            await result_widget.update(f"**Error:** {e}")

    def action_go_back(self) -> None:
        self.app.pop_screen()

    def action_quit(self) -> None:
        self.app.exit()
