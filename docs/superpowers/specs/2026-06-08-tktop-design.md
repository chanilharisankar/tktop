# tktop — Design Specification

**Tool:** tktop — interactive CLI token monitor for coding agents
**Audience:** Personal use first, open-source later
**Date:** 2026-06-08 (last updated: 2026-06-13)

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
| CLI entry point | Typer | Argument parsing, auto-generated help, subcommand support (`tktop config show`). |
| Async HTTP | httpx | Non-blocking LLM API calls. TUI stays responsive during analysis. |
| File watching | watchfiles | Rust-backed, reliable, asyncio-compatible. Tails JSONL transcripts for live updates. |
| Config | python-dotenv + JSON settings file | Standard .env file loading, layered with `~/.tktop/settings.json`. |
| Testing | pytest + pytest-asyncio | Standard, good async support. |
| Linting | ruff | Fast Python linter, covers pycodestyle, pyflakes, isort, bandit, bugbear, pyupgrade. |
| Security | bandit | SAST scanning of source code. |
| Packaging | pyproject.toml + hatchling | Modern Python packaging. pip-installable from git. |

### Installation

```bash
# From source
git clone <repo>
cd tktop
pip install -e ".[dev]"
tktop

# Binary build
make binary  # produces dist/tktop via pyinstaller
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
- `status` — `"idle"` or `"busy"` indicates an active/recent session
- `startedAt` / `updatedAt` — epoch milliseconds
- `pid` — process ID for display
- `version` — Claude Code version string

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

**Session titles** are extracted from `ai-title` type entries.

Other types (`mode`, `system`, `last-prompt`, `permission-mode`, `file-history-snapshot`, `attachment`) are ignored.

### 3.3 Performance Characteristics

Measured on actual data from this machine:

| Operation | Data Size | Time |
|---|---|---|
| Session discovery (13 files) | ~4 KB | < 1 ms |
| Parse largest transcript (1076 turns) | 5.2 MB | 31 ms |
| Parse ALL 84 transcripts | 76.5 MB | 461 ms |
| Parse single new JSONL line | ~1 KB | < 1 ms |

Conclusion: Direct file reads are fast enough. No database needed.

---

## 4. Architecture

### 4.1 Component Diagram

```
tktop (single process)
│
├── CLI Layer (typer)
│   ├── Entry point, arg parsing, launches TUI
│   └── Subcommands: config show, config path
│
├── TUI Layer (textual)
│   ├── OverviewScreen        — live session cards with summary stats
│   ├── DashboardScreen       — btop-style multi-panel monitoring
│   ├── TurnDetailScreen      — single turn drill-down
│   ├── AnalysisScreen        — LLM optimization results
│   ├── HistoryScreen         — 7-day daily usage breakdown
│   ├── HelpScreen            — keybindings and panel documentation
│   └── ProviderPickerScreen  — modal LLM provider selector
│
├── Adapter Layer
│   ├── SessionAdapter        — protocol (interface) for all adapters
│   └── ClaudeCodeAdapter     — reads ~/.claude/ sessions + JSONL transcripts
│
├── Metrics Engine
│   ├── Aggregator            — token/cost accumulation, tool stats, per-turn costs
│   ├── DriftDetector         — 9 detection algorithms
│   └── Pricing               — model → cost-per-token lookup + breakdown
│
└── LLM Provider Layer
    ├── LLMProvider           — protocol (interface) for all providers
    ├── OllamaProvider        — local Ollama instance (uses chat API with system prompt)
    ├── AnthropicProvider     — direct Anthropic API
    ├── VertexProvider        — Anthropic models on Vertex AI
    ├── OpenAIProvider        — any OpenAI-compatible endpoint
    └── ProviderFactory       — config → provider instance
```

### 4.2 Data Flow

```
~/.claude/sessions/*.json ──▶ ClaudeCodeAdapter.discover()
                                    │
                                    ▼
                              list[SessionInfo]
                                    │
                                    ▼
                              OverviewScreen (live cards, auto-refresh every 2s)
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
              Aggregator      DriftDetector    Auto-refresh
              (totals,        (9 algorithms)   (2s interval,
               tool stats,                     incremental
               costs,                          turn append)
               cost_per_turn,                       │
               turn_costs)                          │
                    │               │               │
                    └───────────────┼───────────────┘
                                    ▼
                              DashboardScreen (all panels update reactively)
                                    │
                        ┌───────────┼───────────┐
                        │           │           │
                        ▼           ▼           ▼
                   enter on     press 'a'   press 'h'
                   turn row         │       (from overview)
                        │           │           │
                        ▼           ▼           ▼
                   TurnDetail  AnalysisScreen  HistoryScreen
                               (async LLM,     (7-day daily
                                provider        aggregation)
                                picker)
```

### 4.3 Key Design Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Architecture | Monolith TUI (single process) | 31ms parse time means no need for a daemon or database. Simple to install and run. |
| Async model | Textual's built-in asyncio | Textual is async-native. LLM calls run as `@work` background workers. TUI never blocks. |
| Data persistence | Direct file reads | Performance is excellent. SQLite deferred to future when cross-session analytics and team aggregation are needed. |
| Adapter pattern | Protocol (structural typing) | Adding Cursor/Aider support = implement one protocol. No changes to metrics or TUI layers. |
| Provider pattern | Protocol (structural typing) | Adding a new LLM backend = implement one protocol. Config switch via env var or settings.json. |
| Config layering | settings.json < env vars < in-app selection | Settings file for persistence, env vars for overrides, in-app picker for quick switching. |
| Live updates | Timer-based polling (2s interval) | Simpler than file watching for incremental updates. New turns append to the table without full rebuild. |
| Turn table updates | Incremental append | Only new turns are added to the DataTable. Auto-scroll only if user is already at the bottom — doesn't interrupt browsing. |

---

## 5. User Interface

### 5.1 Navigation

| Key | Action | Scope |
|---|---|---|
| `q` | Quit app | Everywhere — always exits |
| `escape` | Go back one level | Dashboard → Overview, Detail → Dashboard, etc. |
| `enter` | Drill in | Overview → Dashboard, Turn row → Turn Detail |
| `a` | Run LLM analysis | Dashboard only |
| `r` | Refresh data | Overview + Dashboard + History |
| `h` | Open history | Overview only |
| `p` | Pick LLM provider | Analysis only |
| `?` or `F1` | Help screen | Everywhere |
| `↑/↓` or `j/k` | Navigate lists | Session list, turns table |

### 5.2 Screen 1: Overview (Landing Screen)

Shown on launch. Lists all sessions with live-updating statuses for active ones. Sessions are categorized as "active" (status=busy, or status=idle updated within last hour) and "recent" (everything else). Auto-refreshes status every 2 seconds.

Elements:
- **Active sessions** at top with count label, `SessionCard` widgets showing project path, model, duration, cost, token count
- **Recent/completed sessions** below
- Card selection via cursor (↑/↓/j/k) with visual highlight
- Press `enter` to drill into Dashboard
- Press `h` to open 7-day history

### 5.3 Screen 2: Dashboard (btop-inspired)

Full monitoring view for a single session. Multi-panel grid layout. All panels auto-refresh every 2 seconds.

**Layout:**

```
┌─ TOKEN USAGE ────────────────┐┌─ COST ─────────────────────────┐
│                               ││                                │
│ Model: claude-opus-4-6        ││ Total: $1.84   Turns: 142      │
│                               ││                                │
│ Input      ██████████░░ 89k   ││ Cumulative cost time series    │
│ Cache Write████░░░░░░░░ 38k   ││ chart (block characters)       │
│ Cache Read █████████░░░ 72k   ││                                │
│ Output     ██████░░░░░░ 38k   ││ Per-turn cost breakdown table: │
│                               ││ #   Input  Output CaWr  CaRd  │
│ In+Out: 128k  All: 238k      ││ 140 $0.01  $0.05  —     $0.00 │
│                               ││ 141 $0.01  $0.03  —     $0.00 │
│                               ││ 142 $0.01  $0.09  —     $0.00 │
└───────────────────────────────┘└────────────────────────────────┘

┌─ TOKEN FLOW (optional) ──────────────────────────────────────────┐
│ Sparkline graph of output tokens per turn                        │
└──────────────────────────────────────────────────────────────────┘

┌─ TOOLS ──────────────────────┐┌─ ALERTS ────────────────────────┐
│ Tool       Calls  Turns  Bar ││ ⚠ Read loop: Read 4x session   │
│ Bash        399    45    ███ ││ ✖ Token explosion: output       │
│ Read         75    60    ██  ││   doubling each turn            │
│ Edit         82    30    ██  ││                                 │
└──────────────────────────────┘└─────────────────────────────────┘

┌─ TURNS ──────────────────────────────────────────────────────────┐
│ #    Time      Role       Tokens  Tools           What           │
│ 142  10:23:15  assistant  1,400   Bash, Read      Let me check  │
│ 141  10:22:58  user       —       —               fix the bug   │
│ 140  10:22:30  assistant  950     Edit            Found issue   │
└──────────────────────────────────────────────────────────────────┘
```

**Panels:**

| Panel | Widget | Description |
|---|---|---|
| TOKEN USAGE | `TokenBars` | Model name at top, horizontal bars for input/cache-write/cache-read/output with counts and percentages. Summary line shows billable (in+out) and total tokens. |
| COST | `CostGraph` | Total cost + turn count header. Block-character time series chart of cumulative cost over turns. Per-turn cost breakdown table (last 10 turns) with columns: #, Input, Output, CaWr, CaRd, Total. Color-coded to match token bars. |
| TOKEN FLOW | `TokenGraph` (Sparkline) | Optional — enabled by `show_token_flow` config. Braille sparkline of output tokens per turn. |
| TOOLS | `ToolTable` | Tool stats sorted by call count, with calls/turns columns and mini bar charts. |
| ALERTS | `AlertPanel` | Active drift alerts with severity icons and descriptions. |
| TURNS | `DataTable` | Scrollable table of recent turns (last 50 on initial load). Columns: #, Time, Role, Tokens, Tools, What. New turns append incrementally. Auto-scroll only if cursor is at bottom. Press enter to drill into turn detail. |

**Subtitle:** `{project_path} — {model} — ${cost}`

### 5.4 Screen 3: Turn Detail

Drill-down into a single turn. Shows full token breakdown, tool calls with IDs, and content preview.

**Layout:**

```
┌─ TOKEN USAGE ─────────────┐┌─ TOOL CALLS ──────────────────┐
│ Input tokens:       200   ││ 1. Bash  (toolu_01PHvb...)    │
│ Output tokens:    1,200   ││ 2. Read  (toolu_01N8yB...)    │
│ Cache write:          0   ││                               │
│ Cache read:       5,000   ││                               │
│ Cost this turn:  $0.092   ││                               │
└───────────────────────────┘└───────────────────────────────┘

┌─ CONTENT PREVIEW ────────────────────────────────────────────┐
│ Let me check the test file and run the failing test.         │
└──────────────────────────────────────────────────────────────┘
```

**Subtitle:** `Turn #{number} — {role} — {time} — {model}`

### 5.5 Screen 4: LLM Analysis

Triggered by pressing `a` from the Dashboard. Runs async — dashboard remains usable.

- **Summary line** at top showing turn count, billable tokens, cost, tool count, alert count
- **Provider label** showing current LLM provider and model (e.g. `ollama/llama3`)
- **Analysis results** rendered as Markdown in a scrollable view
- Press `p` to switch LLM provider mid-session (opens modal picker, re-runs analysis)
- Error handling for unreachable providers and failed analysis calls

### 5.6 Screen 5: History

7-day daily usage breakdown. Accessed from Overview by pressing `h`.

- **DataTable** with columns: Date, Sessions, Turns, Input, Output, Cache, Cost
- **Total row** at bottom summing all 7 days
- **Cost bars** panel below with horizontal bar chart showing daily cost, highest day marked with `◀`
- Aggregates across ALL sessions for each day

### 5.7 Screen 6: Help

Full documentation of all panels, keybindings, and configuration. Shows:
- Panel descriptions with interpretation guides for Token Flow sparkline patterns
- All 9 drift detection algorithm summaries
- Keybinding reference per screen
- Configuration info (settings file location, CLI commands, load order)

### 5.8 Screen 7: Provider Picker (Modal)

Modal overlay for switching LLM provider during analysis:
- Lists all 4 providers with their configured model
- Active provider marked with `●`
- Selection dismisses modal and re-runs analysis with new provider

---

## 6. Data Models

```python
@dataclass
class TokenUsage:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_tokens: int = 0
    cache_read_tokens: int = 0

    @property
    def total(self) -> int:
        """All tokens (input + output + cache write + cache read)."""
        return (self.input_tokens + self.output_tokens +
                self.cache_creation_tokens + self.cache_read_tokens)

    @property
    def billable(self) -> int:
        """Billable tokens (input + output only, excludes cache)."""
        return self.input_tokens + self.output_tokens


@dataclass
class ToolCall:
    name: str       # "Bash", "Read", "Edit", etc.
    id: str         # tool call ID from API

@dataclass
class Turn:
    number: int
    timestamp: datetime
    role: str               # "user", "assistant"
    model: str | None       # model ID, only on assistant turns
    usage: TokenUsage
    tool_calls: list[ToolCall] = field(default_factory=list)
    content_preview: str = ""  # first 200 chars of text content


@dataclass
class TurnCost:
    turn_number: int
    input_cost: float = 0.0
    output_cost: float = 0.0
    cache_write_cost: float = 0.0
    cache_read_cost: float = 0.0

    @property
    def total(self) -> float:
        return (self.input_cost + self.output_cost +
                self.cache_write_cost + self.cache_read_cost)


@dataclass
class Alert:
    severity: str       # "info", "warning", "critical"
    type: str           # detector name (see section 7)
    description: str
    detected_at: datetime

@dataclass
class ToolStat:
    name: str
    calls: int = 0
    turns_present: int = 0  # how many turns this tool appeared in

@dataclass
class SessionInfo:
    id: str                 # UUID from Claude Code
    pid: int                # process ID
    agent_type: str         # "claude-code"
    project_path: str       # working directory
    model: str              # latest model used
    status: str             # "idle", "busy", "unknown"
    started_at: datetime
    updated_at: datetime
    version: str = ""       # Claude Code version
    title: str = ""         # session title from ai-title entry

@dataclass
class SessionMetrics:
    session: SessionInfo
    turns: list[Turn] = field(default_factory=list)
    total_usage: TokenUsage = field(default_factory=TokenUsage)
    total_cost: float = 0.0
    tool_stats: dict[str, ToolStat] = field(default_factory=dict)
    alerts: list[Alert] = field(default_factory=list)
    tokens_per_turn: list[int] = field(default_factory=list)
    cost_per_turn: list[float] = field(default_factory=list)    # cumulative cost at each assistant turn
    turn_costs: list[TurnCost] = field(default_factory=list)    # per-turn cost breakdown
```

---

## 7. Drift Detection

Nine detection algorithms. Each runs independently over the turn list and returns zero or more alerts. Results are deduped by `type:description` to avoid flooding.

### 7.1 Tool Loop
- **Rule:** Same tool name called ≥ 3 times in 5 consecutive assistant turns (no user turn breaking the streak)
- **Severity:** warning
- **Signal:** Agent is stuck retrying the same approach

### 7.2 Read Loop
- **Rule:** Read tool called ≥ 4 times total across the session
- **Severity:** warning
- **Signal:** Agent keeps re-reading files instead of keeping content in context

### 7.3 Edit Thrash
- **Rule:** Edit/Write tool calls ≥ 5 times in a sliding window of 10 assistant turns
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
- **Rule:** Same tool called 3+ times with user turns interleaved (heuristic for repeated permission denials)
- **Severity:** warning
- **Signal:** Agent keeps trying actions the user is rejecting

### 7.7 Error Retry Loop
- **Rule:** Detected via tool_loop when Bash is the repeated tool
- **Severity:** warning
- **Signal:** Agent keeps running failing commands without changing approach

### 7.8 Cache Miss Streak
- **Rule:** `cache_read_tokens = 0` for ≥ 5 consecutive assistant turns while `cache_creation_tokens > 0`
- **Severity:** warning
- **Signal:** Cache isn't being reused — prompts changing too much between turns

### 7.9 Cost Spike
- **Rule:** Single turn cost > 2× average turn cost for the session (requires ≥ 3 assistant turns)
- **Severity:** info
- **Signal:** One turn is disproportionately expensive

---

## 8. Pricing

### 8.1 Model Pricing Table

| Model | Input (per 1M) | Output (per 1M) | Cache Write (per 1M) | Cache Read (per 1M) |
|---|---|---|---|---|
| claude-opus-4-6 | $15.00 | $75.00 | $18.75 | $1.50 |
| claude-opus-4-8 | $15.00 | $75.00 | $18.75 | $1.50 |
| claude-sonnet-4-6 | $3.00 | $15.00 | $3.75 | $0.30 |
| claude-haiku-4-5 | $0.80 | $4.00 | $1.00 | $0.08 |
| gpt-4o | $2.50 | $10.00 | — | — |
| gpt-4.1 | $2.00 | $8.00 | $0.50 | $0.50 |

Unknown models display tokens but show `$0.00` cost.

### 8.2 Cost Calculation

Two functions:
- `calculate_cost(model, usage) -> float` — total cost for a TokenUsage
- `calculate_cost_breakdown(model, usage) -> tuple[float, float, float, float]` — returns `(input_cost, output_cost, cache_write_cost, cache_read_cost)` for per-component breakdown

### 8.3 Cost Aggregation

The aggregator computes:
- `cost_per_turn: list[float]` — cumulative cost recalculated at each assistant turn (for the time series chart)
- `turn_costs: list[TurnCost]` — per-turn cost breakdown by component (for the breakdown table)
- `total_cost: float` — final cumulative cost

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

| Provider | Implementation | API Endpoint |
|---|---|---|
| Ollama | `OllamaProvider` — uses `/api/chat` with system prompt + user message | Local Ollama instance |
| Anthropic | `AnthropicProvider` — uses `/v1/messages` with API key auth | `api.anthropic.com` |
| Vertex AI | `VertexProvider` — uses rawPredict with gcloud auth token | `{region}-aiplatform.googleapis.com` |
| OpenAI | `OpenAIProvider` — uses `/chat/completions` with Bearer auth | Any OpenAI-compatible endpoint |

### 9.3 System Prompt

The Ollama provider sends a detailed system prompt (`SYSTEM_PROMPT` in `prompt.py`) that:
- Establishes the role as an LLM token usage optimizer
- Explains Claude Code context (autonomous terminal agent)
- Defines what developers CAN control (their prompts, CLAUDE.md, project structure, task delegation, session management)
- Defines what developers CANNOT control (agent system prompt, internal guardrails, tool behavior, reasoning)
- Lists actionable optimization strategies

### 9.4 Analysis Prompt Structure

The `build_analysis_prompt(metrics)` function builds a prompt with:

1. **Session Data** — agent type, model, turn count, token breakdown by category, estimated cost, cache hit ratio
2. **Tool Usage** — each tool with call count and percentage
3. **Detected Issues** — each alert from drift detection with severity
4. **User Prompts** — last 5 user turns with content preview (what the developer asked)
5. **Agent Activity** — last 10 assistant turns with output tokens, tools, and content preview
6. **Instructions** — asks for 3-5 actionable recommendations, each with: observed pattern, why it costs tokens, concrete developer action

### 9.5 Provider Factory

`create_provider(cfg: Config) -> LLMProvider | None` — uses `match` on `cfg.llm_provider` to instantiate the correct provider. Returns `None` for unknown providers.

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

### 10.1 ClaudeCodeAdapter

**Session Discovery (`discover`):**
- Scans `~/.claude/sessions/*.json`
- Parses each file into a `SessionInfo`
- Handles malformed files gracefully (skips)
- Returns sorted by `updated_at` descending (most recent first)

**Transcript Parsing (`parse_transcript`):**
- Finds transcript file: searches `~/.claude/projects/*/` for `{session_id}.jsonl`
- Parses each JSONL line, filtering for `type=assistant` and `type=user`
- Extracts `model`, `usage` (maps `cache_creation_input_tokens` → `cache_creation_tokens`, `cache_read_input_tokens` → `cache_read_tokens`), `tool_calls`, and `content_preview`
- User messages: handles both string and list content formats
- Returns empty list for missing transcripts

---

## 11. Configuration

### 11.1 Load Order (layered, later wins)

1. **Settings file** (`~/.tktop/settings.json`) — auto-created on first run with defaults, `chmod 600`
2. **Environment variables** — from `.env` file or shell
3. **Auto-detection** — Vertex AI settings from Claude Code env vars
4. **In-app selection** — provider picker in analysis screen (session-only, not persisted)

### 11.2 Settings File (`~/.tktop/settings.json`)

```json
{
    "default_provider": "ollama",
    "ui": {
        "show_token_flow": false
    },
    "providers": {
        "ollama": {
            "host": "http://localhost:11434",
            "model": "llama3"
        },
        "anthropic": {
            "api_key": "",
            "model": "claude-sonnet-4-6"
        },
        "vertex": {
            "project": "",
            "region": "us-east5",
            "model": "claude-sonnet-4-6"
        },
        "openai": {
            "base_url": "https://api.openai.com/v1",
            "api_key": "",
            "model": "gpt-4o"
        }
    }
}
```

### 11.3 Environment Variables

```bash
TKTOP_CLAUDE_DIR          # Claude data directory (default: ~/.claude)
TKTOP_LLM_PROVIDER        # ollama | anthropic | vertex | openai
TKTOP_OLLAMA_HOST          # Ollama base URL
TKTOP_OLLAMA_MODEL         # Ollama model name
TKTOP_ANTHROPIC_API_KEY    # Anthropic API key
TKTOP_ANTHROPIC_MODEL      # Anthropic model ID
TKTOP_VERTEX_PROJECT       # GCP project ID
TKTOP_VERTEX_REGION        # GCP region
TKTOP_VERTEX_MODEL         # Model ID on Vertex
TKTOP_OPENAI_BASE_URL      # OpenAI-compatible base URL
TKTOP_OPENAI_API_KEY       # OpenAI API key
TKTOP_OPENAI_MODEL         # OpenAI model ID
TKTOP_SHOW_TOKEN_FLOW      # 1/true/yes to show token flow graph
```

### 11.4 Auto-detection

When Vertex AI env vars from Claude Code are present:
- `ANTHROPIC_VERTEX_PROJECT_ID` → sets `vertex_project` if not already set
- `CLOUD_ML_REGION` → sets `vertex_region` (unless "global")
- `CLAUDE_CODE_USE_VERTEX=1` → switches `llm_provider` to "vertex" (if currently "ollama")

### 11.5 CLI Config Commands

- `tktop config show` — prints resolved config as JSON (API keys masked with `****` prefix)
- `tktop config path` — prints settings file path

### 11.6 Config Dataclass

```python
@dataclass
class Config:
    claude_dir: str = ""
    llm_provider: str = "ollama"
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "llama3"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-6"
    vertex_project: str = ""
    vertex_region: str = "us-east5"
    vertex_model: str = "claude-sonnet-4-6"
    openai_base_url: str = "https://api.openai.com/v1"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"
    show_token_flow: bool = False
```

---

## 12. Widgets

### 12.1 TokenBars (`token_bars.py`)

Renders horizontal bar chart of token usage with Rich Text.

- Displays model name at top (bold cyan) when set
- Four bars: Input (blue), Cache Write (yellow), Cache Read (green), Output (magenta)
- Each bar: label + filled blocks (█) + empty blocks (░) + count + percentage
- Summary line: billable tokens (in+out) and total tokens
- Helper `_fmt(n)`: formats numbers as `1.5M`, `2.5k`, or raw for small values
- `update_usage(usage, model="")`: updates data and refreshes

### 12.2 CostGraph (`cost_graph.py`)

Renders cumulative cost time series chart and per-turn breakdown table.

- **Header**: total cost (bold green) and turn count
- **Chart**: block-character bar chart (height=6, width=min(data_len, 60))
  - Uses `" ▁▂▃▄▅▆▇█"` block characters for fractional fills
  - Y-axis shows min/max cost labels
  - X-axis labeled "turns"
  - Downsamples data via `_sample()` when > 60 data points
- **Breakdown table**: last 10 turns with color-coded columns
  - Columns: #, Input (blue), Output (magenta), CaWr (yellow), CaRd (green), Total (bold)
  - Zero costs shown as `—`
  - Tiny costs (<0.001) shown with 5 decimal places
  - Truncation note when > 10 turns: "N earlier turns hidden"
- `update_data(data, total_cost, turn_count, turn_costs=None)`: updates all data

### 12.3 TokenGraph (`token_graph.py`)

Thin wrapper around Textual's `Sparkline` widget. Shows output tokens per turn as a braille sparkline. Only shown when `show_token_flow=True`.

### 12.4 ToolTable (`tool_table.py`)

DataTable with tool statistics. Sorted by call count descending. Columns: Tool, Calls, Turns, visual bar.

### 12.5 AlertPanel (`alert_panel.py`)

Renders drift detection alerts with severity icons. Warning = ⚠, Critical = ✖.

### 12.6 SessionCard (`session_card.py`)

Compact session summary for the overview screen. Shows status indicator (●/○), agent type, project path, model, duration, cost, token count. Supports selected state with background highlight.

---

## 13. Styling (`styles.tcss`)

Textual CSS stylesheet. Key classes:

| Class | Purpose |
|---|---|
| `.panel` | Bordered section with round border, padding, margin |
| `.panel-title` | Bold warning-colored panel header |
| `.alert-warning` | Warning-colored bold text |
| `.alert-critical` | Error-colored bold text |
| `.session-active` | Success-colored text |
| `.session-inactive` | Muted text |
| `SessionCard` | Height 1, hover highlight, selected highlight (#1a3a3a) |
| `DataTable > .datatable--cursor` | Cursor row highlight (#1a3a3a) |
| `#analysis-scroll` | Bordered scroll area for analysis results |

---

## 14. File Structure

```
tktop/
├── src/
│   └── tktop/
│       ├── __init__.py                # version string
│       ├── cli.py                     # typer entry point + config subcommands
│       ├── config.py                  # layered config: settings.json + env vars + auto-detect
│       ├── adapter/
│       │   ├── __init__.py
│       │   ├── protocol.py            # SessionAdapter protocol
│       │   └── claude.py              # Claude Code adapter (discover + parse)
│       ├── metrics/
│       │   ├── __init__.py
│       │   ├── types.py               # TokenUsage, Turn, TurnCost, Alert, SessionInfo, SessionMetrics, etc.
│       │   ├── pricing.py             # model pricing table + calculate_cost + calculate_cost_breakdown
│       │   ├── aggregator.py          # token/cost aggregation with per-turn breakdowns
│       │   └── drift.py               # 9 drift detection algorithms
│       ├── tui/
│       │   ├── __init__.py
│       │   ├── app.py                 # TktopApp — root app, screen routing, global bindings
│       │   ├── styles.tcss            # Textual CSS stylesheet
│       │   ├── screens/
│       │   │   ├── __init__.py
│       │   │   ├── overview.py        # session list with live cards + auto-refresh
│       │   │   ├── dashboard.py       # btop-style multi-panel monitoring
│       │   │   ├── turn_detail.py     # single turn drill-down
│       │   │   ├── analysis.py        # LLM analysis with provider switching
│       │   │   ├── history.py         # 7-day daily usage breakdown
│       │   │   ├── help.py            # keybindings + panel documentation
│       │   │   └── provider_picker.py # modal LLM provider selector
│       │   └── widgets/
│       │       ├── __init__.py
│       │       ├── token_bars.py      # horizontal token bars with model name
│       │       ├── token_graph.py     # sparkline wrapper (optional)
│       │       ├── cost_graph.py      # time series chart + per-turn breakdown table
│       │       ├── tool_table.py      # tool stats with mini bars
│       │       ├── alert_panel.py     # drift/loop alerts
│       │       └── session_card.py    # overview session card
│       └── llm/
│           ├── __init__.py
│           ├── protocol.py            # LLMProvider protocol
│           ├── prompt.py              # system prompt + analysis prompt builder
│           ├── ollama.py              # Ollama provider (chat API)
│           ├── anthropic_provider.py  # Anthropic direct API provider
│           ├── vertex.py              # Vertex AI provider (gcloud auth)
│           ├── openai_provider.py     # OpenAI-compatible provider
│           └── factory.py             # provider factory
├── tests/
│   ├── conftest.py                    # shared fixtures (fixtures_dir, transcript paths)
│   ├── fixtures/
│   │   ├── session_simple.json        # single session metadata
│   │   ├── transcript_simple.jsonl    # 2-turn transcript (user→assistant→user→assistant)
│   │   ├── transcript_with_tools.jsonl # multi-turn with tool calls (Read, Bash, Edit)
│   │   └── transcript_drift.jsonl     # 5 consecutive Read calls (triggers drift)
│   ├── test_types.py                  # TokenUsage.total, .billable, TurnCost.total
│   ├── test_pricing.py                # cost calculation, cost breakdown, model table
│   ├── test_adapter_claude.py         # session discovery, transcript parsing
│   ├── test_aggregator.py             # token accumulation, tool stats, tokens_per_turn, cost_per_turn, turn_costs
│   ├── test_drift.py                  # all 9 drift detection algorithms
│   ├── test_config.py                 # config loading, env var overrides, vertex auto-detect
│   ├── test_config_settings.py        # settings file creation, loading, permissions
│   ├── test_llm_ollama.py             # Ollama provider (mocked httpx)
│   ├── test_llm_factory.py            # provider factory for all 4 providers
│   ├── test_prompt.py                 # analysis prompt building, system prompt content
│   ├── test_history.py                # daily usage history aggregation
│   ├── test_session_title.py          # session title extraction from transcripts
│   ├── test_token_bars.py             # token bar rendering, model display, _fmt helper
│   ├── test_cost_graph.py             # cost chart rendering, _sample, _cost formatter, breakdown table
│   └── test_integration.py            # end-to-end adapter→aggregator→drift pipeline
├── pyproject.toml                     # package metadata, deps, ruff config, pytest config
├── Makefile                           # install, run, test, lint, security, audit, check, binary, clean
├── .env.example                       # example env var configuration
├── .gitignore                         # Python + editor + build excludes
└── README.md                          # user-facing docs
```

---

## 15. Build & Quality Gates

### 15.1 pyproject.toml

**Dependencies:**
- `textual>=1.0.0`, `rich>=13.0.0`, `typer>=0.12.0`
- `httpx>=0.27.0`, `watchfiles>=0.21.0`, `python-dotenv>=1.0.0`

**Dev dependencies:**
- `pytest>=8.0.0`, `pytest-asyncio>=0.23.0`
- `ruff>=0.8.0`, `bandit>=1.7.0`, `pip-audit>=2.7.0`

**Ruff config:**
- Target: Python 3.13, line length 100
- Rules: E, W, F, I (isort), S (bandit), B (bugbear), UP (pyupgrade)
- Ignores: S603/S607 (subprocess for gcloud), S101 in tests (assert)

### 15.2 Pre-commit Hook (`.git/hooks/pre-commit`)

Runs three checks in order, blocking commit on failure:

1. **Lint:** `ruff check src/ tests/`
2. **SAST:** `bandit -r src/tktop/ -q`
3. **Tests:** `pytest -q`

### 15.3 Makefile Targets

| Target | Command | Description |
|---|---|---|
| `install` | `pip install -e ".[dev]"` | Editable install with dev deps |
| `run` | `python -m tktop.cli` | Launch the TUI |
| `test` | `pytest -v` | Run all tests |
| `lint` | `ruff check src/ tests/` | Lint check |
| `security` | `bandit -r src/tktop/ -q` | SAST scan |
| `audit` | `pip-audit` | Dependency vulnerability scan |
| `check` | `lint + security + test` | Full quality check |
| `binary` | `pyinstaller --onefile ...` | Build standalone binary |
| `clean` | `rm -rf build/ dist/ ...` | Clean build artifacts |

---

## 16. Test Coverage

94 tests across 16 test files. All tests run in <0.3s.

| Test File | Tests | Coverage |
|---|---|---|
| `test_types.py` | 5 | TokenUsage.total, .billable, TurnCost.total |
| `test_pricing.py` | 7 | Opus/Sonnet cost calc, unknown model, model table, cost breakdown, sum consistency |
| `test_adapter_claude.py` | 5 | Session discovery, transcript parsing, content preview, empty dir, missing transcript |
| `test_aggregator.py` | 9 | Token totals, tool stats, tokens_per_turn, cost_per_turn (cumulative, skips user, empty), turn_costs (breakdown, skips user, empty) |
| `test_drift.py` | 12 | All 9 detectors + edge cases (broken by user turn, not triggered, etc.) |
| `test_config.py` | 11 | Defaults, env overrides, vertex auto-detect, show_token_flow, config resolution |
| `test_config_settings.py` | 7 | Settings file creation, loading, permissions, defaults, apply |
| `test_llm_ollama.py` | 3 | Analyze (mocked), error handling, health check |
| `test_llm_factory.py` | 5 | Factory for all 4 providers + unknown |
| `test_prompt.py` | 6 | Prompt building, section presence, system prompt content, user prompts |
| `test_history.py` | 2 | Daily aggregation, empty sessions |
| `test_session_title.py` | 3 | Title extraction from ai-title entries |
| `test_token_bars.py` | 6 | Model display, no model default, model persistence, _fmt helper |
| `test_cost_graph.py` | 12 | _sample, update_data, rendering (waiting, chart, breakdown), truncation, _cost formatter |
| `test_integration.py` | 1 | End-to-end adapter→aggregator→drift pipeline |

---

## 17. Future Work (Not in current version)

Intentionally deferred to keep the scope tight:

- **Server mode** — HTTP/gRPC server to receive metrics from multiple developers for team-wide analysis
- **Agentic multi-step analysis** — LLM agent with tools that can query metrics, compare sessions, investigate patterns autonomously
- **SQLite persistence** — store aggregated metrics for historical trends and cross-session analytics
- **Cursor/Aider adapters** — implement the adapter protocol for other coding agents
- **Homebrew formula** — `brew install tktop` for open-source distribution
- **`--json` output mode** — machine-readable output for scripting and CI/CD integration
- **Custom pricing config** — user-defined model pricing for internal/custom models
- **Export/share reports** — save LLM analysis results as markdown or HTML
