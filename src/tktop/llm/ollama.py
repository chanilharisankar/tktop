import httpx

from tktop.llm.prompt import SYSTEM_PROMPT
from tktop.llm.usage import LLMResult, LLMUsage


class OllamaProvider:
    name = "ollama"

    def __init__(self, host: str, model: str) -> None:
        self.host = host
        self.model = model

    async def analyze(self, prompt: str) -> LLMResult:
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(
                f"{self.host}/api/chat",
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": prompt},
                    ],
                    "stream": False,
                },
            )
            response.raise_for_status()
            data = response.json()
            msg = data.get("message", {})
            return LLMResult(
                text=msg.get("content", data.get("error", "No response")),
                usage=LLMUsage(
                    input_tokens=data.get("prompt_eval_count"),
                    output_tokens=data.get("eval_count"),
                ),
            )

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(self.host)
                return response.status_code == 200
        except httpx.HTTPError:
            return False
