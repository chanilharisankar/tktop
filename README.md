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
# From PyPI
pip install tktop

# Upgrade to the latest release
pip install -U tktop
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
- [x] Codex
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

Local development still uses an editable install:

```bash
pip install -e ".[dev]"
```

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
