# tktop Plan: Add Codex Support and Generalize Agent Adapters

> **Status:** Planned work
>
> **Goal:** Add first-class support for Codex session data and make the codebase
> extensible so additional coding agents can be added without rewriting the UI,
> metrics, or analysis layers.

## 1. Current State

tktop already has the right high-level shape for multi-agent support:

- `src/tktop/adapter/protocol.py` defines a generic `SessionAdapter`
- `src/tktop/metrics/*` operates on normalized `SessionInfo` and `Turn` objects
- `src/tktop/tui/*` consumes those normalized models rather than raw files

The remaining Claude-specific seams are concentrated in a few places:

- `src/tktop/adapter/claude.py` is the only concrete adapter
- `src/tktop/tui/app.py` instantiates `ClaudeCodeAdapter` directly
- `src/tktop/config.py` still exposes `claude_dir`
- UI copy and docs still refer to `~/.claude` in a few empty states and help text
- Tests and fixtures are built around Claude session/transcript shapes

That means the clean path is not a rewrite. The right move is to keep the
normalized domain model, introduce an adapter registry/factory, and add Codex as
another adapter implementation.

## 2. Design Direction

### 2.1 Keep the normalized core

Do not let Codex-specific or Claude-specific file formats leak into the metrics
or TUI layers. The shared core should stay:

- `SessionInfo`
- `Turn`
- `TokenUsage`
- `SessionMetrics`
- `SessionAdapter`

### 2.2 Add a small adapter layer of indirection

Introduce a generic adapter selection layer so the app can choose a concrete
session source from config or auto-detection:

- one factory or registry for adapters
- one adapter-specific config block per agent
- one agent identifier on `SessionInfo.agent_type`

This lets the UI stay agnostic while the adapter handles the file layout and
parsing rules.

### 2.3 Preserve backward compatibility

Existing Claude support should remain the default until Codex support is fully
validated. The current `claude_dir` setting can be retained as a compatibility
alias, but the new shape should prefer a neutral field such as
`agent_data_dir`, `session_root`, or per-adapter configuration.

### 2.4 Make file-format parsing explicit

Codex may not match Claude’s session registry or transcript layout exactly. The
adapter should own these differences and translate them into the common domain
model. If Codex has multiple transcript shapes, keep parser helpers in the
adapter module or a parser submodule rather than branching in the TUI.

## 3. Proposed File/Module Changes

| File | Change |
|---|---|
| `src/tktop/adapter/protocol.py` | Keep the protocol, but ensure it stays source-agnostic and reusable for new agents |
| `src/tktop/adapter/claude.py` | Keep Claude adapter as a reference implementation; extract reusable helpers where it makes sense |
| `src/tktop/adapter/codex.py` | New adapter for Codex session discovery, transcript parsing, and live watch support |
| `src/tktop/adapter/factory.py` | New adapter factory/registry keyed by agent type or config |
| `src/tktop/config.py` | Replace Claude-only config with generic adapter config while preserving compatibility aliases |
| `src/tktop/tui/app.py` | Instantiate adapters through the factory instead of hard-coding Claude |
| `src/tktop/tui/screens/overview.py` | Replace Claude-only empty-state text with neutral agent/session text |
| `src/tktop/tui/screens/history.py` | Keep the logic generic; only update any hard-coded Claude defaults or copy |
| `src/tktop/llm/prompt.py` | Keep the prompt agent-neutral where possible and avoid Claude-only wording unless it is describing the analyzed session |
| `tests/fixtures/*` | Add Codex fixtures alongside the existing Claude fixtures |
| `tests/test_adapter_codex.py` | New adapter tests for Codex discovery, transcript parsing, and watch behavior |
| `tests/test_config.py` | Cover adapter selection and compatibility aliases |

## 4. Implementation Plan

### Phase 1: Define the extensibility seam

- Add a neutral adapter factory or registry
- Keep `SessionAdapter` as the main interface
- Add adapter selection to config, with a default adapter
- Decide whether the app should select adapters by:
  - explicit config value
  - auto-detection by filesystem
  - fallback order when multiple agent roots exist

### Phase 2: Generalize configuration

- Rename Claude-only config fields where necessary
- Keep `claude_dir` as a fallback alias during migration
- Add Codex-specific paths and env vars only if they differ from the generic
  adapter shape
- Update settings file defaults to support multiple agent backends cleanly

### Phase 3: Implement Codex adapter

- Discover Codex sessions from the real local data layout
- Parse Codex transcript files into `SessionInfo` and `Turn`
- Map Codex usage fields into `TokenUsage`
- Extract tool calls, timestamps, session titles, and model names
- Implement `watch()` if the Codex format supports live tailing

### Phase 4: Update UI and prompts

- Remove Claude-specific empty-state copy
- Keep agent label and project/session path display generic
- Make analysis prompt wording describe the selected session’s agent type
- Keep the current cost and drift logic unchanged

### Phase 5: Add tests and fixtures

- Add Codex session and transcript fixtures
- Add parser tests for discovery and transcript parsing
- Add a compatibility test that ensures Claude still works
- Add an integration test that exercises the new adapter through the same
  metrics pipeline as Claude

### Phase 6: Validate and document

- Run the full test suite
- Verify the overview, dashboard, history, and analysis flows with Codex data
- Update README and design docs with the supported agents list

## 5. Acceptance Criteria

The work is complete when:

- Codex sessions and transcripts load in the existing UI
- The dashboard, history view, drift detection, cost analysis, and turn detail
  screens all work without agent-specific branching outside the adapter layer
- Claude support still works
- Adding another coding agent requires implementing a new adapter and adding
  tests, not rewriting the app

## 6. Open Questions

- What is the exact local Codex session/transcript layout on this machine?
- Does Codex expose a session registry comparable to Claude’s JSON files?
- Are session titles and tool-call shapes already available in Codex logs, or
  do they need fallback parsing?
- Should the default config remain Claude-first for compatibility, or move to a
  generic auto-detect flow once Codex lands?

## 7. Recommended Execution Order

1. Inspect real Codex files and confirm the schema
2. Add the adapter factory and generic config shape
3. Implement `CodexAdapter`
4. Add tests and fixtures
5. Remove the remaining Claude-only UI copy
6. Update docs and release notes
