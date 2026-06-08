# tktop — Design Specification

**Tool:** tktop — interactive CLI token monitor for coding agents
**Audience:** Personal use first, open-source later
**Date:** 2026-06-08

---

## 1. Problem Statement

LLM coding agents (Claude Code, Cursor, Aider) consume tokens opaquely. Developers have no visibility into where tokens burn, which tools are expensive, whether the agent is drifting in loops, or how to optimize usage. There is no `htop` equivalent for AI spend.

tktop solves this by reading agent session data directly from local files, presenting a real-time interactive dashboard, detecting wasteful patterns, and providing LLM-powered optimization suggestions.

---

## 2. Tech Stack

| Component | Technology | Rationale |
|---|---|---|
| Language | Python 3.13+ | Agentic LLM ecosystem is Python-first (Anthropic SDK, LangChain, etc.). Already installed. Textual provides excellent TUI. Future server/agentic features benefit from Python. |
| TUI framework | Textual | Full-screen interactive apps, CSS-based styling, async-native, built-in widgets (DataTable, TabbedContent, Sparkline), mouse support. btop-level UI quality. |
| Terminal formatting | Rich | Beautiful tables, progress bars, colors. Textual is built on Rich. |
| CLI entry point | Typer | Argument parsing, auto-generated help. |
| Async HTTP | httpx | Non-blocking LLM API calls. TUI stays responsive during analysis. |
| File watching | watchfiles | Rust-backed, reliable, asyncio-compatible. Tails JSONL transcripts for live updates. |
| Config | python-dotenv | Standard .env file loading. |
| Testing | pytest + pytest-asyncio | Standard, good async support. |
| Packaging | pyproject.toml + hatchling | Modern Python packaging. pip-installable from git (GitLab/GitHub). |

### Installation

```bash
# From GitLab (private)
pipx install git+ssh://git@gitlab.company.com/team/tktop.git

# From PyPI (future, open-source)
pipx install tktop

# From source
git clone <repo>
cd tktop
pip install -e .
tktop
```

---

## 3. Data Sources

### 3.1 Claude Code Session Registry

**Location:** `~/.claude/sessions/*.json`

Each file is named `{pid}.json`. Structure:

```json
{
    "pid": 75545,
    "sessionId": "2d72ed26-87e8-4cc8-aea7-8889cf21db56",
    "cwd": "/Users/dev/myproject",
    "startedAt": 1779721776875,
    "version": "2.1.150",
    "kind": "interactive",
    "entrypoint": "cli",
    "status": "idle",
    "updatedAt": 1780732023365
}
```

Fields used:
- `sessionId` — unique identifier, maps to transcript filename
- `cwd` — project working directory
- `status` — `"idle"` indicates an active/recent session
- `startedAt` / `updatedAt` — epoch milliseconds
- `pid` — process ID for display

### 3.2 Transcript Logs

**Location:** `~/.claude/projects/{encoded-cwd}/{sessionId}.jsonl`

The directory name encodes the absolute path with `/` replaced by `-`:
```
/Users/dev/myproject → -Users-dev-myproject
```

Each line is a JSON object with a `type` field. Relevant types:

**`assistant` type — contains token data and tool calls:**

```json
{
    "type": "assistant",
    "timestamp": "2026-06-07T17:56:41.073Z",
    "message": {
        "model": "claude-opus-4-6",
        "role": "assistant",
        "content": [
            {"type": "text", "text": "Let me check..."},
            {"type": "tool_use", "name": "Bash", "id": "toolu_01PHvb..."}
        ],
        "usage": {
            "input_tokens": 3,
            "cache_creation_input_tokens": 38137,
            "cache_read_input_tokens": 0,
            "output_tokens": 405
        }
    },
    "sessionId": "d29b219c-..."
}
```

**`user` type — marks user interaction points:**

```json
{
    "type": "user",
    "timestamp": "2026-06-07T17:56:32.411Z",
    "message": {"role": "user", "content": "fix the bug"},
    "sessionId": "d29b219c-..."
}
```

Other types (`mode`, `system`, `ai-title`, `last-prompt`, `permission-mode`, `file-history-snapshot`, `attachment`) are ignored.

### 3.3 Performance Characteristics

Measured on actual data from this machine:

| Operation | Data Size | Time |
|---|---|---|
| Session discovery (13 files) | ~4 KB | < 1 ms |
| Parse largest transcript (1076 turns) | 5.2 MB | 31 ms |
| Parse ALL 84 transcripts | 76.5 MB | 461 ms |
| Parse single new JSONL line | ~1 KB | < 1 ms |

Conclusion: Direct file reads are fast enough for v1. No database needed.

---

## 4. Architecture

### 4.1 Component Diagram

```
tktop (single process)
│
├── CLI Layer (typer)
│   └── Entry point, arg parsing, launches TUI
│
├── TUI Layer (textual)
│   ├── OverviewScreen      — live session cards with summary stats
│   ├── DashboardScreen     — btop-style multi-panel monitoring
│   ├── TurnDetailScreen    — single turn drill-down
│   └── AnalysisScreen      — LLM optimization results
│
├── Adapter Layer
│   ├── SessionAdapter      — protocol (interface) for all adapters
│   └── ClaudeCodeAdapter   — reads ~/.claude/ sessions + JSONL transcripts
│
├── Metrics Engine
│   ├── Aggregator          — token/cost accumulation, tool stats
│   ├── DriftDetector       — 9 detection algorithms
│   └── Pricing             — model → cost-per-token lookup
│
├── File Watcher (watchfiles)
│   └── Tails JSONL files, pushes new turns via async messages
│
└── LLM Provider Layer
    ├── LLMProvider         — protocol (interface) for all providers
    ├── OllamaProvider      — local Ollama instance
    ├── AnthropicProvider   — direct Anthropic API
    ├── VertexProvider      — Anthropic models on Vertex AI
    └── OpenAIProvider      — any OpenAI-compatible endpoint
```

### 4.2 Data Flow

```
~/.claude/sessions/*.json ──▶ ClaudeCodeAdapter.discover()
                                    │
                                    ▼
                              list[SessionInfo]
                                    │
                                    ▼
                              OverviewScreen (live cards, live-tailing all active)
                                    │
                                    │ user presses enter
                                    ▼
~/.claude/projects/*/{id}.jsonl ──▶ ClaudeCodeAdapter.parse_transcript()
                                    │
                                    ▼
                              list[Turn]
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
              Aggregator      DriftDetector    File Watcher
              (totals,        (9 algorithms)   (tails JSONL,
               tool stats,                     streams new turns)
               costs)                               │
                    │               │               │
                    └───────────────┼───────────────┘
                                    ▼
                              DashboardScreen (all panels update reactively)
                                    │
                                    │ user presses 'a'
                                    ▼
                              LLM Provider (async, non-blocking)
                                    │
                                    ▼
                              AnalysisScreen
```

### 4.3 Key Design Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Architecture | Monolith TUI (single process) | 31ms parse time means no need for a daemon or database. Simple to install and run. |
| Async model | Textual's built-in asyncio | Textual is async-native. File watching and LLM calls run as background workers. TUI never blocks. |
| Data persistence | Direct file reads (v1) | Performance is excellent. SQLite deferred to future when cross-session analytics and team aggregation are needed. |
| File watching | watchfiles (Rust-backed) | More reliable than watchdog. Native asyncio support. Efficient for long-running file tailing. |
| LLM calls | httpx async | Non-blocking. Dashboard stays fully interactive during 2-10 second analysis calls. |
| Adapter pattern | Protocol (structural typing) | Adding Cursor/Aider support = implement one protocol. No changes to metrics or TUI layers. |
| Provider pattern | Protocol (structural typing) | Adding a new LLM backend = implement one protocol. Config switch via env var. |

---

## 5. User Interface

### 5.1 Navigation

| Key | Action | Scope |
|---|---|---|
| `q` | Quit app | Everywhere — always exits |
| `escape` | Go back one level | Dashboard → Overview, Detail → Dashboard |
| `enter` | Drill in | Overview → Dashboard, Turn row → Turn Detail |
| `a` | Run LLM analysis | Dashboard only |
| `r` | Refresh data | Overview + Dashboard |
| `ctrl+c` | Force quit | Everywhere |
| `↑/↓` or `j/k` | Navigate lists | Session list, turns table |

### 5.2 Screen 1: Overview (Landing Screen)

Shown on launch. Lists all sessions with live-updating stats for active ones.

```
╭─ tktop ─────────────────────────────────────────────────────────────────╮
│                                                                         │
│  ACTIVE SESSIONS                                              2 active  │
│                                                                         │
│  ● claude-code   ~/Dev/tktop          opus-4-6     23m   $1.84  142.8k │
│    ██████████████░░░░░░  in:89k  cache:38k  out:15k   ⚠ Read loop      │
│                                                                         │
│  ● claude-code   ~/Dev/api-server     sonnet-4-6   1h2m  $4.12  312.0k │
│    █████████████████████░  in:198k  cache:67k  out:47k                  │
│                                                                         │
│  RECENT SESSIONS                                                        │
│                                                                         │
│  ○ claude-code   ~/Dev/frontend       gpt-4o       2h ago $0.43  45.0k │
│  ○ claude-code   ~/Dev/infra          sonnet-4-6   5h ago $2.10 189.0k │
│                                                                         │
│  ─────────────────────────────────────────────────────────────────────  │
│  Total today: $8.49 across 4 sessions                                   │
│                                                                         │
│  ↑/↓ navigate • enter drill-down • r refresh • q quit                   │
╰─────────────────────────────────────────────────────────────────────────╯
```

Elements:
- **Active sessions** at top with `●` indicator, live-updating token counts and spend
- Mini token bar per session showing input/cache/output ratio at a glance
- Drift alert badges visible from overview (e.g., `⚠ Read loop`)
- **Recent/completed sessions** below with `○` indicator
- **Daily total spend** summary at bottom
- Persistent keybinding help in footer

### 5.3 Screen 2: Dashboard (btop-inspired)

Full monitoring view for a single session. Multi-panel grid layout inspired by btop.

```
╭─ tktop ── ~/Dev/tktop ── claude-opus-4-6 ── 23m ── $1.84 ─────── idle ─╮
│                                                                          │
│ ╭─ Token Usage ─────────────────────╮╭─ Cost Breakdown ────────────────╮ │
│ │                                   ││                                 │ │
│ │ Input      ██████████░░░░  89.2k  ││  Input       $0.0013           │ │
│ │ Cache Write████░░░░░░░░░░  38.1k  ││  Cache Write $0.0071           │ │
│ │ Cache Read █████████░░░░░  72.0k  ││  Cache Read  $0.0001           │ │
│ │ Output     ██████░░░░░░░░  38.4k  ││  Output      $1.8300           │ │
│ │                                   ││  ─────────────────             │ │
│ │ Total: 237.7k tokens              ││  Total:       $1.84            │ │
│ ╰───────────────────────────────────╯╰─────────────────────────────────╯ │
│                                                                          │
│ ╭─ Token Flow ──────────────────────────────────────────────────────────╮│
│ │ 2.1k│        ╭╮                  ╭──╮                                ││
│ │     │   ╭──╮╭╯│    ╭╮      ╭╮  ╭╯  ╰╮     ╭╮                       ││
│ │     │╭╮╭╯  ╰╯ ╰──╮╭╯╰╮╭──╮│╰──╯    ╰╮╭╮╭╮│╰╮                     ││
│ │  0  │╰╯╰╯        ╰╯  ╰╯  ╰╯         ╰╯╰╯╰╯ ╰─                    ││
│ │     └──────────────────────────────────────────── turns ──────────   ││
│ ╰───────────────────────────────────────────────────────────────────────╯│
│                                                                          │
│ ╭─ Tools ──────────────────────────╮╭─ Alerts ─────────────────────────╮ │
│ │ Tool          Calls   Tokens     ││                                  │ │
│ │ Bash           399    14.8k  ███ ││ ⚠ Read loop: same file 4x in    │ │
│ │ Read            75     8.2k  ██  ││   last 8 turns                   │ │
│ │ Edit            82     9.6k  ██  ││                                  │ │
│ │ Write           24     7.2k  █   ││ ✖ Token explosion: output        │ │
│ │ WebFetch         3     4.1k  █   ││   doubling each turn             │ │
│ ╰──────────────────────────────────╯╰──────────────────────────────────╯ │
│                                                                          │
│ ╭─ Turns ───────────────────────────────────────────────────────────────╮│
│ │ #    Time      Role       In     Out    Cache   Tools                ││
│ │ 142  10:23:15  assistant  200    1.2k   5.0k    Bash, Read          ││
│ │ 141  10:22:58  user       —      —      —       —                   ││
│ │ 140  10:22:30  assistant  150    800    5.0k    Edit                ││
│ │ 139  10:22:10  assistant  120    450    5.0k    Bash, Bash          ││
│ │ ▼ scroll for more                                                   ││
│ ╰───────────────────────────────────────────────────────────────────────╯│
│                                                                          │
│  a analyze • r refresh • enter turn detail • esc back • q quit           │
╰──────────────────────────────────────────────────────────────────────────╯
```

Panels:
- **Token Usage** — horizontal bars showing input/cache-write/cache-read/output with counts and percentages
- **Cost Breakdown** — per-category cost in USD
- **Token Flow** — braille sparkline graph showing output tokens per turn over time, scrolls live
- **Tools** — table sorted by call count with mini bar charts
- **Alerts** — active drift alerts with severity icons (⚠ warning, ✖ critical)
- **Turns** — scrollable table of recent turns with token breakdown per turn

All panels update in real-time as new turns stream in from the file watcher.

### 5.4 Screen 3: Turn Detail

Drill-down into a single turn. Accessed by pressing `enter` on a turn row.

```
╭─ Turn #142 ── assistant ── 10:23:15 ── claude-opus-4-6 ─────────────────╮
│                                                                          │
│ ╭─ Token Usage ────────────────────╮╭─ Tool Calls ─────────────────────╮ │
│ │                                  ││                                  │ │
│ │ Input tokens:           200      ││ 1. Bash  (toolu_01PHvb...)       │ │
│ │ Output tokens:        1,200      ││ 2. Read  (toolu_01N8yB...)       │ │
│ │ Cache write:              0      ││                                  │ │
│ │ Cache read:           5,000      ││                                  │ │
│ │ Cost this turn:      $0.092      ││                                  │ │
│ ╰──────────────────────────────────╯╰──────────────────────────────────╯ │
│                                                                          │
│ ╭─ Content Preview ─────────────────────────────────────────────────────╮│
│ │ Let me check the test file and run the failing test.                  ││
│ │                                                                       ││
│ │ [tool_use: Bash] git status                                          ││
│ │ [tool_use: Read] /Users/khari.../src/main.py                         ││
│ ╰───────────────────────────────────────────────────────────────────────╯│
│                                                                          │
│  esc back to dashboard • q quit                                          │
╰──────────────────────────────────────────────────────────────────────────╯
```

### 5.5 Screen 4: LLM Analysis

Triggered by pressing `a` from the Dashboard. Runs async — dashboard remains usable.

```
╭─ tktop ── Analysis ── ~/Dev/tktop ── powered by ollama/llama3 ──────────╮
│                                                                          │
│ ╭─ Session Summary Sent to LLM ────────────────────────────────────────╮ │
│ │ 142 turns • 237.7k tokens • $1.84 • 5 tools • 2 drift alerts        │ │
│ ╰──────────────────────────────────────────────────────────────────────╯ │
│                                                                          │
│ ╭─ Optimization Recommendations ───────────────────────────────────────╮ │
│ │                                                                      │ │
│ │ INPUT OPTIMIZATION                                                   │ │
│ │ 1. Cache hit ratio is 30% — your system prompt is being re-sent     │ │
│ │    frequently. Consider structuring prompts to maximize the 5-min   │ │
│ │    cache TTL window by batching related requests.                    │ │
│ │                                                                      │ │
│ │ GUARDRAIL ADVICE                                                     │ │
│ │ 2. Read loop detected — the agent read the same file 4 times in     │ │
│ │    8 turns. Add file content to context on first read instead of    │ │
│ │    re-reading. Consider using CLAUDE.md to pre-load key files.      │ │
│ │                                                                      │ │
│ │ TOOL PRUNING                                                         │ │
│ │ 3. Bash accounts for 399 calls (53% of all tool use). Review       │ │
│ │    whether some calls could be replaced with Read or combined.      │ │
│ │                                                                      │ │
│ ╰──────────────────────────────────────────────────────────────────────╯ │
│                                                                          │
│  esc back to dashboard • q quit                                          │
╰──────────────────────────────────────────────────────────────────────────╯
```

---

## 6. Data Models

```python
@dataclass
class SessionInfo:
    id: str                    # UUID from Claude Code
    pid: int                   # process ID
    agent_type: str            # "claude-code"
    project_path: str          # working directory
    model: str                 # latest model used
    status: str                # "idle", "active", "completed"
    started_at: datetime
    updated_at: datetime
    version: str               # Claude Code version

@dataclass
class TokenUsage:
    input_tokens: int
    output_tokens: int
    cache_creation_tokens: int
    cache_read_tokens: int

    @property
    def total(self) -> int:
        return (self.input_tokens + self.output_tokens +
                self.cache_creation_tokens + self.cache_read_tokens)

@dataclass
class ToolCall:
    name: str                  # "Bash", "Read", "Edit", etc.
    id: str                    # tool call ID

@dataclass
class Turn:
    number: int
    timestamp: datetime
    role: str                  # "user", "assistant", "system"
    model: str | None
    usage: TokenUsage
    tool_calls: list[ToolCall]
    content_preview: str       # first 200 chars of text content (truncated)

@dataclass
class Alert:
    severity: str              # "info", "warning", "critical"
    type: str                  # detector name (see section 7)
    description: str
    detected_at: datetime

@dataclass
class ToolStat:
    name: str
    calls: int
    turns_present: int         # how many turns this tool appeared in

@dataclass
class SessionMetrics:
    session: SessionInfo
    turns: list[Turn]
    total_usage: TokenUsage
    total_cost: float
    tool_stats: dict[str, ToolStat]
    alerts: list[Alert]
    tokens_per_turn: list[int] # for the sparkline graph
```

---

## 7. Drift Detection

Nine detection algorithms. Each runs independently over the turn list and returns zero or more alerts.

### 7.1 Tool Loop
- **Rule:** Same tool name called ≥ 3 times in 5 consecutive assistant turns (no user turn breaking the streak)
- **Severity:** warning
- **Signal:** Agent is stuck retrying the same approach

### 7.2 Read Loop
- **Rule:** Same file path appearing in Read tool calls ≥ 4 times in a session
- **Severity:** warning
- **Signal:** Agent keeps re-reading a file instead of keeping it in context

### 7.3 Edit Thrash
- **Rule:** Same file path in Edit/Write tool calls ≥ 5 times in 10 turns
- **Severity:** critical
- **Signal:** Agent is making changes, reverting, changing again — not converging

### 7.4 Token Explosion
- **Rule:** Output tokens per turn increasing > 2× for 3 consecutive assistant turns
- **Severity:** warning
- **Signal:** Agent's responses are growing unbounded — possible reasoning spiral

### 7.5 Runaway Session
- **Rule:** ≥ 10 consecutive assistant turns with no user message AND total output tokens in that streak > 500k
- **Severity:** critical
- **Signal:** Agent is running unsupervised and burning tokens

### 7.6 Permission Loop
- **Rule:** Agent hitting permission denials ≥ 3 times in 5 turns
- **Severity:** warning
- **Signal:** Agent keeps trying actions the user is rejecting

### 7.7 Error Retry Loop
- **Rule:** Bash tool returning non-zero exit codes ≥ 3 times in 5 turns
- **Severity:** warning
- **Signal:** Agent keeps running failing commands without changing approach

### 7.8 Cache Miss Streak
- **Rule:** cache_read_tokens = 0 for ≥ 5 consecutive assistant turns while cache_creation_tokens > 0
- **Severity:** warning
- **Signal:** Cache isn't being reused — prompts changing too much between turns

### 7.9 Cost Spike
- **Rule:** Single turn cost > 2× average turn cost for the session
- **Severity:** info
- **Signal:** One turn is disproportionately expensive

---

## 8. Pricing

Model pricing table for cost calculation:

| Model | Input (per 1M) | Output (per 1M) | Cache Write (per 1M) | Cache Read (per 1M) |
|---|---|---|---|---|
| claude-opus-4-6 | $15.00 | $75.00 | $18.75 | $1.50 |
| claude-opus-4-8 | $15.00 | $75.00 | $18.75 | $1.50 |
| claude-sonnet-4-6 | $3.00 | $15.00 | $3.75 | $0.30 |
| claude-haiku-4-5 | $0.80 | $4.00 | $1.00 | $0.08 |
| gpt-4o | $2.50 | $10.00 | — | — |
| gpt-4.1 | $2.00 | $8.00 | $0.50 | $0.50 |

Unknown models display tokens but show `$0.00` cost with a visual indicator that pricing is unavailable.

---

## 9. LLM Diagnostics Engine

### 9.1 Provider Interface

```python
class LLMProvider(Protocol):
    name: str

    async def analyze(self, prompt: str) -> str:
        """Send analysis prompt, return response text."""
        ...

    async def health_check(self) -> bool:
        """Check if the provider is reachable."""
        ...
```

### 9.2 Supported Providers

| Provider | Config Env Vars | Description |
|---|---|---|
| Ollama | `TKTOP_LLM_PROVIDER=ollama`, `TKTOP_OLLAMA_HOST`, `TKTOP_OLLAMA_MODEL` | Local Ollama instance. Default provider. |
| Anthropic | `TKTOP_LLM_PROVIDER=anthropic`, `TKTOP_ANTHROPIC_API_KEY`, `TKTOP_ANTHROPIC_MODEL` | Direct Anthropic API |
| Vertex AI | `TKTOP_LLM_PROVIDER=vertex`, `TKTOP_VERTEX_PROJECT`, `TKTOP_VERTEX_REGION`, `TKTOP_VERTEX_MODEL` | Self-hosted Anthropic models on Google Cloud Vertex AI |
| OpenAI-compatible | `TKTOP_LLM_PROVIDER=openai`, `TKTOP_OPENAI_BASE_URL`, `TKTOP_OPENAI_API_KEY`, `TKTOP_OPENAI_MODEL` | Any OpenAI-compatible endpoint (vLLM, Together, etc.) |

### 9.3 Analysis Prompt Structure

The prompt sent to the LLM has five sections:

1. **Session Summary** — agent type, model, duration, turn count, total tokens by category, total cost
2. **Tool Usage Table** — each tool with call count and percentage of total
3. **Detected Issues** — each alert from drift detection with severity
4. **Conversation Samples** — last 10 turns with `content_preview` text; turns that triggered drift alerts with surrounding context
5. **Instructions** — output 3-5 actionable recommendations categorized as:
   - **Input Optimization** — reducing prompt/context tokens
   - **Guardrail Advice** — preventing drift and loops
   - **Tool Pruning** — reducing tool call overhead

The conversation samples enable the LLM to suggest prompt-level optimizations (e.g., "your system prompt is verbose" or "the agent keeps re-reading files because the initial instruction was ambiguous").

---

## 10. Adapter Interface

```python
class SessionAdapter(Protocol):
    name: str

    async def discover(self) -> list[SessionInfo]:
        """Find all known sessions (active + recent)."""
        ...

    async def parse_transcript(self, session_id: str) -> list[Turn]:
        """Parse full transcript for a session."""
        ...

    async def watch(self, session_id: str) -> AsyncIterator[Turn]:
        """Stream new turns as they're written to the transcript."""
        ...
```

v1 implements `ClaudeCodeAdapter` only. The protocol is ready for future `CursorAdapter`, `AiderAdapter`, and `GenericJSONLAdapter`.

---

## 11. Configuration

All configuration via environment variables. Loaded from `.env` file if present.

```bash
# Claude data directory (default: ~/.claude)
TKTOP_CLAUDE_DIR=~/.claude

# LLM provider: ollama | anthropic | vertex | openai
TKTOP_LLM_PROVIDER=ollama

# Ollama
TKTOP_OLLAMA_HOST=http://localhost:11434
TKTOP_OLLAMA_MODEL=llama3

# Anthropic (direct)
TKTOP_ANTHROPIC_API_KEY=sk-ant-...
TKTOP_ANTHROPIC_MODEL=claude-sonnet-4-6

# Vertex AI (Anthropic on GCP)
TKTOP_VERTEX_PROJECT=my-project
TKTOP_VERTEX_REGION=us-central1
TKTOP_VERTEX_MODEL=claude-sonnet-4-6

# OpenAI-compatible
TKTOP_OPENAI_BASE_URL=https://api.openai.com/v1
TKTOP_OPENAI_API_KEY=sk-...
TKTOP_OPENAI_MODEL=gpt-4o
```

---

## 12. File Structure

```
tktop/
├── src/
│   └── tktop/
│       ├── __init__.py
│       ├── cli.py                  # typer entry point
│       ├── config.py               # env/dotenv config loading
│       ├── adapter/
│       │   ├── __init__.py
│       │   ├── protocol.py         # SessionAdapter protocol
│       │   └── claude.py           # Claude Code adapter
│       ├── metrics/
│       │   ├── __init__.py
│       │   ├── types.py            # SessionInfo, Turn, ToolCall, Alert, etc.
│       │   ├── aggregator.py       # token/cost accumulation, tool stats
│       │   ├── drift.py            # 9 drift detection algorithms
│       │   └── pricing.py          # model pricing table
│       ├── tui/
│       │   ├── __init__.py
│       │   ├── app.py              # root Textual app, screen routing
│       │   ├── screens/
│       │   │   ├── __init__.py
│       │   │   ├── overview.py     # session list with live cards
│       │   │   ├── dashboard.py    # btop-style monitoring dashboard
│       │   │   ├── turn_detail.py  # single turn drill-down
│       │   │   └── analysis.py     # LLM analysis results
│       │   ├── widgets/
│       │   │   ├── __init__.py
│       │   │   ├── token_bars.py   # horizontal token breakdown bars
│       │   │   ├── token_graph.py  # braille sparkline graph
│       │   │   ├── tool_table.py   # tool stats with mini bars
│       │   │   ├── alert_panel.py  # drift/loop alerts
│       │   │   └── session_card.py # overview session card
│       │   └── styles.tcss         # Textual CSS stylesheet
│       └── llm/
│           ├── __init__.py
│           ├── protocol.py         # LLMProvider protocol
│           ├── prompt.py           # analysis prompt builder
│           ├── ollama.py           # Ollama provider
│           ├── anthropic.py        # Anthropic direct provider
│           ├── vertex.py           # Vertex AI provider
│           └── openai.py           # OpenAI-compatible provider
├── tests/
│   ├── conftest.py                 # shared fixtures
│   ├── fixtures/
│   │   ├── session_simple.json
│   │   ├── transcript_simple.jsonl
│   │   ├── transcript_with_tools.jsonl
│   │   └── transcript_drift.jsonl
│   ├── test_adapter_claude.py
│   ├── test_aggregator.py
│   ├── test_drift.py
│   ├── test_pricing.py
│   └── test_llm_ollama.py
├── pyproject.toml
├── .env.example
├── .gitignore
├── Makefile
└── README.md
```

---

## 13. Future Work (Not in v1)

Intentionally deferred to keep the initial scope tight:

- **Server mode** — HTTP/gRPC server to receive metrics from multiple developers for team-wide analysis
- **Agentic multi-step analysis** — LLM agent with tools that can query the metrics DB, compare sessions, investigate patterns autonomously
- **SQLite persistence** — store aggregated metrics for historical trends and cross-session analytics
- **Cursor/Aider adapters** — implement the adapter protocol for other coding agents
- **Homebrew formula** — `brew install tktop` for open-source distribution
- **`--json` output mode** — machine-readable output for scripting and CI/CD integration
- **Custom pricing config** — user-defined model pricing for internal/custom models
- **Export/share reports** — save LLM analysis results as markdown or HTML
