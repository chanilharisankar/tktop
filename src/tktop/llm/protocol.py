from typing import Protocol, runtime_checkable


@runtime_checkable
class LLMProvider(Protocol):
    name: str

    async def analyze(self, prompt: str) -> str: ...

    async def health_check(self) -> bool: ...
