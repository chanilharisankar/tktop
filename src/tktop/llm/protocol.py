from typing import Protocol, runtime_checkable

from tktop.llm.usage import LLMResult


@runtime_checkable
class LLMProvider(Protocol):
    name: str

    async def analyze(self, prompt: str) -> LLMResult: ...

    async def health_check(self) -> bool: ...
