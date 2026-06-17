import httpx

from tktop.llm.prompt import SYSTEM_PROMPT
from tktop.llm.usage import LLMResult, LLMUsage


class OpenAIProvider:
    name = "openai"

    def __init__(self, base_url: str, api_key: str, model: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model

    async def analyze(self, prompt: str) -> LLMResult:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": prompt},
                    ],
                    "max_tokens": 4096,
                },
            )
            response.raise_for_status()
            data = response.json()
            usage_data = data.get("usage", {})
            prompt_tokens = usage_data.get("prompt_tokens")
            prompt_details = usage_data.get("prompt_tokens_details") or {}
            cached_tokens = prompt_details.get("cached_tokens", 0)
            input_tokens = None
            if prompt_tokens is not None:
                input_tokens = max(0, prompt_tokens - cached_tokens)
            return LLMResult(
                text=data["choices"][0]["message"]["content"],
                usage=LLMUsage(
                    input_tokens=input_tokens,
                    output_tokens=usage_data.get("completion_tokens"),
                    cache_read_tokens=cached_tokens,
                ),
            )

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    f"{self.base_url}/models",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                )
                return response.status_code == 200
        except httpx.HTTPError:
            return False
