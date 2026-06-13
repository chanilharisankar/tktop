import json
import tomllib
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from pathlib import Path

from tktop.metrics.types import SessionInfo, TokenUsage, ToolCall, Turn


class CodexAdapter:
    name = "codex"

    def __init__(self, base_dir: str) -> None:
        self.base_dir = Path(base_dir)
        self.default_model = self._read_default_model()
        self._session_index = self._read_session_index()

    @classmethod
    def is_available(cls, base_dir: str) -> bool:
        root = Path(base_dir)
        return root.exists() and (root / "sessions").exists()

    async def discover(self) -> list[SessionInfo]:
        sessions_dir = self.base_dir / "sessions"
        if not sessions_dir.exists():
            return []

        sessions: list[SessionInfo] = []
        seen: set[str] = set()

        for path in sessions_dir.rglob("*.jsonl"):
            meta = self._read_session_meta(path)
            if meta is None:
                continue

            session_id = str(meta.get("id", "")).strip()
            if not session_id or session_id in seen:
                continue
            seen.add(session_id)

            index_entry = self._session_index.get(session_id, {})
            started_at = self._parse_timestamp(meta.get("timestamp"))
            if started_at is None:
                started_at = datetime.fromtimestamp(path.stat().st_mtime, tz=UTC)

            updated_at = self._parse_timestamp(index_entry.get("updated_at"))
            if updated_at is None:
                updated_at = datetime.fromtimestamp(path.stat().st_mtime, tz=UTC)

            sessions.append(
                SessionInfo(
                    id=session_id,
                    pid=0,
                    agent_type="codex",
                    project_path=str(meta.get("cwd", "")),
                    model=self.default_model,
                    status="idle",
                    started_at=started_at,
                    updated_at=updated_at,
                    version=str(meta.get("cli_version", "")),
                    title=str(index_entry.get("thread_name", "")),
                )
            )

        sessions.sort(key=lambda s: s.updated_at, reverse=True)
        return sessions

    async def parse_transcript(self, session_id: str) -> list[Turn]:
        transcript_path = self._find_transcript(session_id)
        if transcript_path is None:
            return []

        turns: list[Turn] = []
        current_turn: Turn | None = None
        last_assistant_turn: Turn | None = None
        turn_number = 0

        for raw_line in transcript_path.read_text().splitlines():
            line = raw_line.strip()
            if not line:
                continue

            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue

            payload = entry.get("payload", {})
            if not isinstance(payload, dict):
                continue

            entry_type = entry.get("type")
            payload_type = payload.get("type")

            if entry_type == "event_msg" and payload_type == "token_count":
                if last_assistant_turn is not None:
                    info = payload.get("info", {})
                    if isinstance(info, dict):
                        last = info.get("last_token_usage", {})
                        if isinstance(last, dict):
                            last_assistant_turn.usage = TokenUsage(
                                input_tokens=int(last.get("input_tokens", 0) or 0),
                                output_tokens=int(last.get("output_tokens", 0) or 0),
                                cache_creation_tokens=0,
                                cache_read_tokens=int(
                                    last.get("cached_input_tokens", 0) or 0
                                ),
                            )
                continue

            if entry_type != "response_item":
                continue

            if payload_type == "message":
                role = payload.get("role")
                if role == "developer":
                    continue
                if role not in ("user", "assistant"):
                    continue

                if current_turn is not None:
                    turns.append(current_turn)

                turn_number += 1
                timestamp = self._parse_timestamp(
                    entry.get("timestamp") or payload.get("timestamp")
                )
                current_turn = Turn(
                    number=turn_number,
                    timestamp=timestamp,
                    role=role,
                    model=self.default_model if role == "assistant" else None,
                    usage=TokenUsage(),
                    tool_calls=[],
                    content_preview=self._extract_preview(payload),
                )
                if role == "assistant":
                    last_assistant_turn = current_turn
                continue

            if current_turn is None or current_turn.role != "assistant":
                continue

            if payload_type in ("function_call", "custom_tool_call"):
                call_name = str(payload.get("name", ""))
                call_id = str(
                    payload.get("call_id")
                    or payload.get("id")
                    or f"{current_turn.number}-{len(current_turn.tool_calls) + 1}"
                )
                current_turn.tool_calls.append(ToolCall(name=call_name, id=call_id))
                continue

            if payload_type == "function_call_output":
                continue

        if current_turn is not None:
            turns.append(current_turn)

        for turn in reversed(turns):
            if turn.role == "assistant" and not turn.model:
                turn.model = self.default_model or None
                break

        return turns

    async def watch(self, session_id: str) -> AsyncIterator[Turn]:
        raise NotImplementedError
        yield  # type: ignore[misc]

    def _find_transcript(self, session_id: str) -> Path | None:
        sessions_dir = self.base_dir / "sessions"
        if not sessions_dir.exists():
            return None

        for path in sessions_dir.rglob(f"*{session_id}.jsonl"):
            if path.is_file():
                return path
        return None

    def _read_session_index(self) -> dict[str, dict[str, str]]:
        index_path = self.base_dir / "session_index.jsonl"
        if not index_path.exists():
            return {}

        index: dict[str, dict[str, str]] = {}
        try:
            for raw_line in index_path.read_text().splitlines():
                line = raw_line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                session_id = str(entry.get("id", "")).strip()
                if not session_id:
                    continue
                index[session_id] = {
                    "thread_name": str(entry.get("thread_name", "")),
                    "updated_at": str(entry.get("updated_at", "")),
                }
        except OSError:
            return {}
        return index

    def _read_session_meta(self, path: Path) -> dict | None:
        try:
            with path.open() as f:
                for raw_line in f:
                    line = raw_line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if entry.get("type") == "session_meta":
                        payload = entry.get("payload")
                        if isinstance(payload, dict):
                            return payload
                        return None
        except OSError:
            return None
        return None

    def _read_default_model(self) -> str:
        config_path = self.base_dir / "config.toml"
        if not config_path.exists():
            return ""

        try:
            with config_path.open("rb") as f:
                data = tomllib.load(f)
        except (OSError, tomllib.TOMLDecodeError):
            return ""

        model = data.get("model")
        return model if isinstance(model, str) else ""

    @staticmethod
    def _extract_preview(payload: dict) -> str:
        parts: list[str] = []
        for block in payload.get("content", []):
            if not isinstance(block, dict):
                continue
            block_type = block.get("type")
            if block_type == "input_text":
                text = block.get("text", "")
            elif block_type == "output_text":
                text = block.get("text", "")
            else:
                continue
            if text:
                parts.append(str(text))
        return " ".join(parts)[:200]

    @staticmethod
    def _parse_timestamp(value: object) -> datetime:
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                pass
        return datetime.now(tz=UTC)
