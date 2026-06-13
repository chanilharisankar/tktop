# tktop

Token monitor for coding agents. Like `htop` for your AI spend.

## Features

- **Live dashboard** — real-time token usage breakdown (input/output/cache)
- **Token flow graph** — sparkline showing output tokens per turn
- **Tool stats** — see which tools consume the most calls
- **Drift detection** — 9 algorithms detecting loops, thrashing, runaway sessions
- **Cost tracking** — per-session cost estimates by model
- **Turn drill-down** — inspect individual turns with token split and content preview
- **LLM analysis** — on-demand optimization suggestions via Ollama/Anthropic/Vertex AI/OpenAI

## Install

```bash
# From source
git clone <repo>
cd tktop
pip install -e ".[dev]"
tktop
```

## Usage

```bash
tktop              # launch interactive session list
```

### Keybindings

| Key | Action |
|-----|--------|
| `↑/↓` or `j/k` | Navigate |
| `enter` | Select / drill-down |
| `a` | Run LLM analysis |
| `r` | Refresh |
| `escape` | Back |
| `q` | Quit |

## Supported Agents

- [x] Claude Code
- [ ] Cursor (planned)
- [ ] Aider (planned)

## LLM Analysis

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
# Edit .env with your provider settings
```

Supported providers: `ollama` (default), `anthropic`, `vertex`, `openai`

## Development

```bash
make install  # install in dev mode
make test     # run tests
make clean    # clean build artifacts
```

Repository instructions for Codex are in [`AGENTS.md`](AGENTS.md). The current
design is documented in
[`docs/specs/2026-06-08-tktop-design.md`](docs/specs/2026-06-08-tktop-design.md).
