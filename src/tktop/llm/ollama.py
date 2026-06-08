import httpx


class OllamaProvider:
    name = "ollama"

    def __init__(self, host: str, model: str) -> None:
        self.host = host
        self.model = model

    async def analyze(self, prompt: str) -> str:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.host}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                },
            )
            response.raise_for_status()
            return response.json()["response"]

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(self.host)
                return response.status_code == 200
        except httpx.HTTPError:
            return False
