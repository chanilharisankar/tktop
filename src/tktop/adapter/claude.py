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

        sessions.sort(key=lambda s: s.updated_at, reverse=True)
        return sessions

    async def parse_transcript(self, session_id: str) -> list[Turn]:
        raise NotImplementedError

    async def watch(self, session_id: str) -> AsyncIterator[Turn]:
        raise NotImplementedError
        yield  # type: ignore[misc]
