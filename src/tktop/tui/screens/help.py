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
   • Input       — Fresh tokens sent (not cached). Usually small after turn 1.
   • Cache Write — Tokens written to Anthropic's server-side cache. 1.25x input rate.
   • Cache Read  — Tokens served from cache. 10x cheaper. High % = good.
   • Output      — Tokens the model generated. Most expensive. Dominates cost.

 TOKEN FLOW
   Graph showing output tokens per turn over time. Each bar = one turn.

   • ▁▁▁▁▁▁▁  Flat/low    — short, efficient responses

   • ▁▂▃▅▇█  Rising      — token explosion, responses growing each turn

   • ▁█▁█▁█  Spiky       — mix of tool calls and long explanations

   • ▁▁▁████  Late spike  — agent went verbose recently, check why

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

 Overview:    ↑/↓ navigate  enter select  h history  r refresh  q quit
 Dashboard:   a analyze  enter turn detail  r refresh  escape back  q quit
 Analysis:    p pick provider  escape back  q quit
 History:     r refresh  escape back  q quit
 All:         ? this help  q quit

 CONFIGURATION
 ─────────────

 Settings file: ~/.tktop/settings.json (auto-created on first run)
 CLI commands:  tktop config show  |  tktop config path
 Load order:    settings.json < env vars < in-app selection
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
