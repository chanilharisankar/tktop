import dataclasses

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.screen import Screen
from textual.widgets import Footer, Header, Markdown, Static

from tktop.coach.cache import (
    build_cache_entry,
    get_cached_entry,
    with_enhanced_markdown,
)
from tktop.coach.prompt import build_coach_enhancement_prompt
from tktop.coach.rules import build_coach_report, render_coach_markdown
from tktop.coach.types import CoachCacheEntry
from tktop.config import Config
from tktop.llm.factory import create_provider
from tktop.llm.labels import provider_label
from tktop.metrics.types import SessionMetrics


class CoachScreen(Screen):
    BINDINGS = [
        Binding("escape", "go_back", "Back"),
        Binding("l", "enhance", "Enhance"),
        Binding("r", "regenerate", "Regenerate"),
        Binding("q", "quit", "Quit"),
    ]

    def __init__(self, metrics: SessionMetrics, config: Config, **kwargs) -> None:
        super().__init__(**kwargs)
        self.metrics = metrics
        self.config = dataclasses.replace(config)
        self.entry: CoachCacheEntry | None = None

    def compose(self) -> ComposeResult:
        summary = (
            f" {len(self.metrics.turns)} turns | "
            f"{self.metrics.total_usage.billable:,} billable tokens | "
            f"${self.metrics.total_cost:.2f} | "
            f"{len(self.metrics.alerts)} alerts"
        )

        yield Header()
        yield Static(f" SESSION: {summary}", id="coach-summary")
        yield Static(
            f" COACH  (LLM enhancement available: {provider_label(self.config)})",
            classes="panel-title",
            id="coach-title",
        )
        yield VerticalScroll(
            Markdown("*Preparing local coaching...*", id="coach-local"),
            Markdown("", id="coach-enhanced"),
            id="coach-scroll",
        )
        yield Footer()

    def on_mount(self) -> None:
        self._update_subtitle()
        self._load_or_build_report()

    def _update_subtitle(self) -> None:
        self.sub_title = (
            f"Coach — {self.metrics.session.project_path} — "
            f"enhance with {provider_label(self.config)}"
        )

    def _cache(self) -> dict[str, CoachCacheEntry]:
        cache = getattr(self.app, "coach_cache", None)
        if cache is None:
            cache = {}
            self.app.coach_cache = cache
        return cache

    def _load_or_build_report(self, *, regenerate: bool = False) -> CoachCacheEntry:
        cache = self._cache()
        entry = None if regenerate else get_cached_entry(cache, self.metrics)

        if entry is None:
            report = build_coach_report(self.metrics)
            local_markdown = render_coach_markdown(report)
            entry = build_cache_entry(self.metrics, report, local_markdown)
            cache[self.metrics.session.id] = entry

        self.entry = entry
        self._render_entry(entry)
        return entry

    def _render_entry(self, entry: CoachCacheEntry) -> None:
        self.query_one("#coach-local", Markdown).update(entry.local_markdown)
        enhanced_widget = self.query_one("#coach-enhanced", Markdown)
        if entry.enhanced_markdown:
            enhanced_widget.update(entry.enhanced_markdown)
            return

        enhanced_widget.update(
            "\n".join(
                [
                    "## Enhanced Coaching",
                    "",
                    f"Configured model: `{provider_label(self.config)}`",
                    "",
                    "Press `L` to generate contextual coaching suggestions.",
                    "",
                    "Enhanced suggestions are cached in memory until this session changes, "
                    "the app closes, or you regenerate them.",
                ]
            )
        )

    @work(exclusive=True)
    async def _enhance(self) -> None:
        entry = self._load_or_build_report()
        enhanced_widget = self.query_one("#coach-enhanced", Markdown)
        label = provider_label(self.config)
        await enhanced_widget.update(
            f"## Enhanced Coaching\n\nEnhancing suggestions with `{label}`..."
        )

        provider = create_provider(self.config)
        if provider is None:
            await enhanced_widget.update(
                f"## Enhanced Coaching\n\n**Error:** unknown LLM provider "
                f"`{self.config.llm_provider}`.\n\nLocal coaching is still available."
            )
            return

        healthy = await provider.health_check()
        if not healthy:
            await enhanced_widget.update(
                f"## Enhanced Coaching\n\n**Error:** `{provider.name}` is not reachable. "
                "Check your configuration.\n\nLocal coaching is still available."
            )
            return

        prompt = build_coach_enhancement_prompt(self.metrics, entry.report)
        try:
            result = await provider.analyze(prompt)
        except Exception as exc:
            await enhanced_widget.update(
                f"## Enhanced Coaching\n\n**Error:** {exc}\n\n"
                "Local coaching is still available."
            )
            return

        enhanced_markdown = "\n".join(
            [
                "## Enhanced Coaching",
                "",
                f"Model: `{label}`",
                "",
                result,
            ]
        )
        updated_entry = with_enhanced_markdown(entry, enhanced_markdown, label)
        self._cache()[self.metrics.session.id] = updated_entry
        self.entry = updated_entry
        await enhanced_widget.update(enhanced_markdown)

    def action_enhance(self) -> None:
        self._enhance()

    def action_regenerate(self) -> None:
        self._load_or_build_report(regenerate=True)

    def action_go_back(self) -> None:
        self.app.pop_screen()

    def action_quit(self) -> None:
        self.app.exit()
