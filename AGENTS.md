# Codex Repository Instructions

## Project

`tktop` is a Python 3.13+ Textual TUI for monitoring token usage, cost, tools,
and drift in coding-agent sessions. The current adapter reads Claude Code
session metadata and JSONL transcripts from `~/.claude`.

## Source Of Truth

- Product and architecture specification: `docs/specs/2026-06-08-tktop-design.md`
- Historical implementation record: `docs/plans/2026-06-08-tktop.md`
- User-facing setup and usage: `README.md`

The implementation record documents how the current code was built. Do not
replay its completed tasks or embedded commit steps. For new work, inspect the
current code and tests first, then update the specification when behavior or
architecture changes.

## Repository Layout

- `src/tktop/adapter/`: coding-agent session adapters
- `src/tktop/metrics/`: data models, aggregation, pricing, and drift detection
- `src/tktop/llm/`: analysis prompts and provider integrations
- `src/tktop/tui/`: Textual application, screens, widgets, and styles
- `tests/`: unit and integration tests with local fixtures

## Development Commands

```bash
make install
make test
make lint
make security
make check
make run
```

Run focused tests while iterating, then run `make check` before committing.
`make audit` performs the optional dependency vulnerability scan.

## Engineering Conventions

- Preserve the adapter and provider protocols when adding implementations.
- Keep blocking file or network work out of the Textual UI event loop.
- Handle malformed or missing external session data gracefully.
- Add or update tests for behavior changes.
- Keep Ruff compatibility with Python 3.13 and the configured 100-character
  line length.
- Never commit API keys, `.env`, local session data, or generated build output.
- Do not modify files under `.git/`; local hooks are not portable project
  configuration.

## Documentation

- Keep Claude-specific names when they describe supported product behavior,
  model IDs, environment variables, or the Claude Code data format.
- Keep agent workflow instructions vendor-neutral and compatible with Codex.
- Use `docs/specs/` for current design documentation and `docs/plans/` for
  implementation plans or historical execution records.
