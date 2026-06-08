from datetime import datetime, timezone

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.message import Message
from textual.screen import Screen
from textual.widgets import Footer, Header, Static

from tktop.adapter.protocol import SessionAdapter
from tktop.metrics.types import SessionInfo
from tktop.tui.widgets.session_card import SessionCard


class SessionSelected(Message):
    def __init__(self, session: SessionInfo) -> None:
        super().__init__()
        self.session = session


class OverviewScreen(Screen):
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("r", "refresh", "Refresh"),
        Binding("enter", "select", "Select"),
        Binding("up,k", "cursor_up", "Up", show=False),
        Binding("down,j", "cursor_down", "Down", show=False),
    ]

    def __init__(self, adapter: SessionAdapter, **kwargs) -> None:
        super().__init__(**kwargs)
        self.adapter = adapter
        self.sessions: list[SessionInfo] = []
        self.cursor = 0

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static(" SESSIONS", classes="panel-title")
        yield VerticalScroll(id="session-list")
        yield Footer()

    def on_mount(self) -> None:
        self.load_sessions()
        self.set_interval(2, self._auto_refresh)

    @work
    async def load_sessions(self) -> None:
        all_sessions = await self.adapter.discover()
        container = self.query_one("#session-list", VerticalScroll)
        await container.remove_children()

        if not all_sessions:
            await container.mount(Static(" No sessions found in ~/.claude/sessions/"))
            return

        now = datetime.now(tz=timezone.utc)
        active = [
            s for s in all_sessions
            if s.status == "busy"
            or (s.status == "idle" and (now - s.updated_at).total_seconds() < 3600)
        ]
        recent = [s for s in all_sessions if s not in active]

        self.sessions = active + recent
        idx = 0

        if active:
            await container.mount(Static(f" ACTIVE SESSIONS ({len(active)})", classes="panel-title"))
            for session in active:
                card = SessionCard(session, id=f"session-{idx}")
                await container.mount(card)
                idx += 1

        if recent:
            await container.mount(Static(f"\n RECENT SESSIONS ({len(recent)})", classes="panel-title"))
            for session in recent:
                card = SessionCard(session, id=f"session-{idx}")
                await container.mount(card)
                idx += 1

        if not self.sessions:
            await container.mount(Static(" No active or recent sessions"))
            return

        self.cursor = 0
        self._update_selection()

    def _update_selection(self) -> None:
        for i, card in enumerate(self.query(SessionCard)):
            card.selected = i == self.cursor

    def action_cursor_up(self) -> None:
        if self.cursor > 0:
            self.cursor -= 1
            self._update_selection()

    def action_cursor_down(self) -> None:
        if self.cursor < len(self.sessions) - 1:
            self.cursor += 1
            self._update_selection()

    def action_select(self) -> None:
        if self.sessions:
            self.post_message(SessionSelected(self.sessions[self.cursor]))

    def _auto_refresh(self) -> None:
        self._refresh_statuses()

    @work
    async def _refresh_statuses(self) -> None:
        updated = await self.adapter.discover()
        status_map = {s.id: s.status for s in updated}

        changed = False
        for session in self.sessions:
            new_status = status_map.get(session.id)
            if new_status and new_status != session.status:
                session.status = new_status
                changed = True

        if changed:
            for card in self.query(SessionCard):
                card.refresh()

    def action_refresh(self) -> None:
        self.load_sessions()

    def action_quit(self) -> None:
        self.app.exit()
