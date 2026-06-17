# tktop

Token monitor for coding agents. Like `htop` for your AI spend.

## Features

- **Live dashboard** — real-time token usage breakdown (input/output/cache)
- **Token flow graph** — sparkline showing output tokens per turn
- **Tool stats** — see which tools consume the most calls
- **Drift detection** — 9 algorithms detecting loops, thrashing, runaway sessions
- **Cost tracking** — per-session cost estimates by model
- **Turn drill-down** — inspect individual turns with token split and content preview
- **Coach screen** — local feedback on prompt scope, validation habits, checkpoints, and agent workflow smells
- **LLM analysis** — on-demand optimization suggestions via Ollama/Anthropic/Vertex AI/OpenAI

## Install

Requires Python 3.10 or newer.

```bash
# From PyPI
pip install tktop

# Upgrade to the latest release
pip install -U tktop
```

## Usage

```bash
tktop              # launch interactive session list
tktop -h           # show help
tktop -v           # show version
tktop info         # print environment summary for bug reports
tktop doctor       # diagnose local setup
```

`tktop doctor` checks the settings file, Claude/Codex data directories, adapter
discovery, and selected LLM provider configuration without contacting external
LLM APIs.

### Keybindings

| Key | Action |
|-----|--------|
| `↑/↓` or `j/k` | Navigate |
| `enter` | Select / drill-down |
| `a` | Run LLM analysis |
| `c` | Open Coach for the current session |
| `L` | Enhance Coach suggestions with the configured LLM |
| `r` | Refresh |
| `escape` | Back |
| `q` | Quit |

## Supported Agents

- [x] Claude Code
- [x] Codex
- [ ] Cursor (planned)
- [ ] Aider (planned)

## Coach And LLM Analysis

The Coach screen is available from a session dashboard with `c`. It renders a
scrollable Markdown report with local, deterministic guidance about how the
developer used the coding agent: prompt scope, validation requests, checkpoint
habits, exploration before edits, repeated tool usage, and which model tier
would fit similar prompts next time.

Coach does not call an LLM by default. Press `L` inside Coach to enhance the
local findings with the configured analysis provider and model. Enhanced
suggestions are cached in memory for the running TUI session, so leaving and
reopening Coach shows the same result until the session changes, the app closes,
or you regenerate it.

Analyze and Enhanced Coach show an **LLM Call Cost** meter for the analysis call
itself. Before the call completes, tktop shows the estimated prompt input tokens;
after completion, it updates with actual input/output tokens and estimated cost
when the provider returns usage data. Cached Enhanced Coach results are marked
as cached so it is clear no new tokens were spent.

Coach's **Model Fit** section is vendor-neutral. It recommends a tier such as
`cheap_fast`, `balanced`, or `strong_reasoning` based on prompt scope, task
complexity, validation signals, drift, and tool usage. Enhanced Coach can refine
that advice, but it does not need an LLM to produce the local recommendation.

LLM analysis remains available from a session dashboard with `a`. Analysis
focuses on token, cost, drift, and tool optimization; Coach focuses on improving
developer workflow with agentic coding tools.

The settings file is created at `~/.tktop/settings.json` the first time `tktop`
loads its configuration. View its path and resolved values with:

```bash
tktop config path
tktop config show
```

Example configuration:

```json
{
  "session_adapter": "auto",
  "default_provider": "ollama",
  "ui": {
    "show_token_flow": false
  },
  "agents": {
    "claude": {
      "dir": "~/.claude"
    },
    "codex": {
      "dir": "~/.codex"
    }
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

`session_adapter` accepts `auto`, `claude`, or `codex`. Supported analysis
providers are `ollama`, `anthropic`, `vertex`, and `openai`.

Environment variables override `settings.json`. Common overrides are:

```bash
TKTOP_SESSION_ADAPTER=codex
TKTOP_CODEX_DIR=~/.codex
TKTOP_LLM_PROVIDER=openai
TKTOP_OPENAI_API_KEY=sk-...
TKTOP_OPENAI_MODEL=gpt-4o
```

For source checkouts, `.env.example` lists all supported environment variables.
Prefer environment variables for API keys instead of storing secrets in JSON.

## Development

```bash
make install  # install in dev mode
make test     # run tests
make clean    # clean build artifacts
```

Local development still uses an editable install:

```bash
pip install -e ".[dev]"
```

Use these commands while developing:

```bash
make run           # run directly from the editable source checkout
make check         # lint, security scan, and full tests
make package-test  # build and install the wheel in an isolated local venv
make package-run   # launch the locally built wheel
```

`make package-test` uses `.venvs/package-test`, which is ignored by git. It
tests the same wheel artifact that would be uploaded to PyPI, without publishing
anything.

For maintainers, a versioned release can be prepared with:

```bash
make release VERSION=0.1.1
```

### Devbox

If you have the Devbox CLI installed, you can bootstrap the repo with:

```bash
devbox shell
```

On first entry, the shell creates `.venv`, installs `.[dev]`, and activates the
environment for the session.

License: MIT. See [LICENSE](LICENSE).

Repository instructions for Codex are in [`AGENTS.md`](AGENTS.md). The current
design is documented in
[`docs/specs/2026-06-08-tktop-design.md`](docs/specs/2026-06-08-tktop-design.md).
