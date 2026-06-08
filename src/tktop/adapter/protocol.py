from collections.abc import AsyncIterator
from typing import Protocol, runtime_checkable

from tktop.metrics.types import SessionInfo, Turn


@runtime_checkable
class SessionAdapter(Protocol):
    name: str

    async def discover(self) -> list[SessionInfo]: ...

    async def parse_transcript(self, session_id: str) -> list[Turn]: ...

    async def watch(self, session_id: str) -> AsyncIterator[Turn]: ...
