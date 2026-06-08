from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.screen import Screen
from textual.widgets import Footer, Header, Static

HELP_TEXT = """\


 PANELS
 ──────


 TOKEN USAGE

   Breakdown of tokens sent to and received from the LLM.

   • Input       — Fresh tokens sent (not cached).
                   Usually small after turn 1.

   • Cache Write — Tokens written to Anthropic's server-side prompt cache.
                   Costs 1.25x input rate but only happens once per context.

   • Cache Read  — Tokens served from cache. 10x cheaper than input.
                   High cache read % = efficient = good.

   • Output      — Tokens the model generated (responses, thinking, tool calls).
                   Most expensive per-token. Usually dominates your cost.


 TOKEN FLOW

   Graph showing output tokens per turn over time.
   Each bar represents one assistant turn.

   Flat and low = efficient responses.
   Rising pattern = possible drift.
   Sudden spike = check that turn for unexpected behavior.


 TOOLS

   Which tools the agent called and how often.
   High call counts for Read/Edit on the same file may indicate loops.


 ALERTS

   Drift detection findings. 9 algorithms watch for:

   • Tool loop         — same tool 3+ times in 5 turns
   • Read loop         — same file read 4+ times
   • Edit thrash       — same file edited 5+ times in 10 turns

   • Token explosion   — output doubling 3 turns in a row
   • Runaway session   — 10+ turns with no user, 500k+ output

   • Permission loop   — 3+ permission denials
   • Error retry       — 3+ failed bash commands

   • Cache miss streak — 5+ turns with no cache reuse
   • Cost spike        — one turn costing 2x the average



 KEYBINDINGS
 ───────────


 Overview Screen

   ↑/↓ or j/k    Navigate sessions
   enter          Open session dashboard
   h              Daily usage history
   r              Refresh session list
   q              Quit


 Dashboard Screen

   a              Run LLM analysis
   enter          Drill into selected turn
   r              Refresh data
   escape         Back to overview
   q              Quit


 History / Turn Detail / Analysis

   r              Refresh (history only)
   escape         Back
   q              Quit


 All Screens

   ?              This help screen
   q              Quit

"""


class HelpScreen(Screen):
    BINDINGS = [
        Binding("escape", "go_back", "Back"),
        Binding("q", "quit", "Quit"),
        Binding("question_mark", "go_back", "Back", show=False),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield VerticalScroll(Static(HELP_TEXT))
        yield Footer()
        self.sub_title = "Help"

    def action_go_back(self) -> None:
        self.app.pop_screen()

    def action_quit(self) -> None:
        self.app.exit()
