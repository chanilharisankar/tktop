import json
from collections.abc import AsyncIterator
from datetime import datetime, timezone
from pathlib import Path

from tktop.metrics.types import (
    SessionInfo,
    TokenUsage,
    ToolCall,
    Turn,
)


class ClaudeCodeAdapter:
    name = "claude-code"

    def __init__(self, base_dir: str) -> None:
        self.base_dir = Path(base_dir)

    async def discover(self) -> list[SessionInfo]:
        sessions_dir = self.base_dir / "sessions"
        if not sessions_dir.exists():
            return []

        sessions: list[SessionInfo] = []
        for path in sessions_dir.glob("*.json"):
            try:
                data = json.loads(path.read_text())
            except (json.JSONDecodeError, OSError):
                continue

            sessions.append(
                SessionInfo(
                    id=data["sessionId"],
                    pid=data.get("pid", 0),
                    agent_type="claude-code",
                    project_path=data.get("cwd", ""),
                    model="",
                    status=data.get("status", "unknown"),
                    started_at=datetime.fromtimestamp(
                        data["startedAt"] / 1000, tz=timezone.utc
                    ),
                    updated_at=datetime.fromtimestamp(
                        data.get("updatedAt", data["startedAt"]) / 1000,
                        tz=timezone.utc,
                    ),
                    version=data.get("version", ""),
                )
            )

        for session in sessions:
            session.title = self._read_title(session.id)

        sessions.sort(key=lambda s: s.updated_at, reverse=True)
        return sessions

    async def parse_transcript(self, session_id: str) -> list[Turn]:
        transcript_path = self._find_transcript(session_id)
        if transcript_path is None:
            return []

        turns: list[Turn] = []
        turn_number = 0

        for line in transcript_path.read_text().splitlines():
            line = line.strip()
            if not line:
                continue

            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue

            entry_type = entry.get("type")
            if entry_type not in ("assistant", "user"):
                continue

            msg = entry.get("message", {})
            if not isinstance(msg, dict):
                continue

            turn_number += 1
            usage_data = msg.get("usage") or {}
            content_blocks = msg.get("content", [])
            if isinstance(content_blocks, str):
                content_blocks = [{"type": "text", "text": content_blocks}]

            tool_calls: list[ToolCall] = []
            text_parts: list[str] = []

            for block in content_blocks:
                if not isinstance(block, dict):
                    continue
                if block.get("type") == "tool_use":
                    tool_calls.append(
                        ToolCall(name=block.get("name", ""), id=block.get("id", ""))
                    )
                elif block.get("type") == "text":
                    text_parts.append(block.get("text", ""))

            preview = " ".join(text_parts)[:200]
            timestamp_str = entry.get("timestamp", "")
            try:
                timestamp = datetime.fromisoformat(
                    timestamp_str.replace("Z", "+00:00")
                )
            except (ValueError, AttributeError):
                timestamp = datetime.now(tz=timezone.utc)

            turns.append(
                Turn(
                    number=turn_number,
                    timestamp=timestamp,
                    role=entry_type,
                    model=msg.get("model"),
                    usage=TokenUsage(
                        input_tokens=usage_data.get("input_tokens", 0),
                        output_tokens=usage_data.get("output_tokens", 0),
                        cache_creation_tokens=usage_data.get(
                            "cache_creation_input_tokens", 0
                        ),
                        cache_read_tokens=usage_data.get(
                            "cache_read_input_tokens", 0
                        ),
                    ),
                    tool_calls=tool_calls,
                    content_preview=preview,
                )
            )

        return turns

    def _find_transcript(self, session_id: str) -> Path | None:
        projects_dir = self.base_dir / "projects"
        if not projects_dir.exists():
            return None

        filename = f"{session_id}.jsonl"
        for project_dir in projects_dir.iterdir():
            if not project_dir.is_dir():
                continue
            candidate = project_dir / filename
            if candidate.exists():
                return candidate

        return None

    def _read_title(self, session_id: str) -> str:
        transcript_path = self._find_transcript(session_id)
        if transcript_path is None:
            return ""

        try:
            with open(transcript_path) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if entry.get("type") == "ai-title":
                        return entry.get("aiTitle", "")
        except OSError:
            pass

        return ""

    async def watch(self, session_id: str) -> AsyncIterator[Turn]:
        raise NotImplementedError
        yield  # type: ignore[misc]
