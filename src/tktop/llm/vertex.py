import subprocess  # nosec B404 — needed for gcloud auth

import httpx

from tktop.llm.prompt import SYSTEM_PROMPT
from tktop.llm.usage import LLMResult, LLMUsage


class VertexProvider:
    name = "vertex"

    def __init__(self, project: str, region: str, model: str) -> None:
        self.project = project
        self.region = region
        self.model = model

    async def analyze(self, prompt: str) -> LLMResult:
        token = self._get_access_token()

        url = (
            f"https://{self.region}-aiplatform.googleapis.com/v1/"
            f"projects/{self.project}/locations/{self.region}/"
            f"publishers/anthropic/models/{self.model}:rawPredict"
        )

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                url,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                json={
                    "anthropic_version": "vertex-2023-10-16",
                    "max_tokens": 4096,
                    "system": SYSTEM_PROMPT,
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
            response.raise_for_status()
            data = response.json()
            usage = data.get("usage", {})
            return LLMResult(
                text=data["content"][0]["text"],
                usage=LLMUsage(
                    input_tokens=usage.get("input_tokens"),
                    output_tokens=usage.get("output_tokens"),
                    cache_creation_tokens=usage.get("cache_creation_input_tokens", 0),
                    cache_read_tokens=usage.get("cache_read_input_tokens", 0),
                ),
            )

    async def health_check(self) -> bool:
        try:
            self._get_access_token()
            return True
        except (FileNotFoundError, subprocess.TimeoutExpired, RuntimeError):
            return False

    def _get_access_token(self) -> str:
        result = subprocess.run(  # nosec B603 B607 — hardcoded gcloud command
            ["gcloud", "auth", "print-access-token"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            raise RuntimeError(f"gcloud auth failed: {result.stderr}")
        return result.stdout.strip()
