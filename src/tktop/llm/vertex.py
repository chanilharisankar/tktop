import subprocess

import httpx


class VertexProvider:
    name = "vertex"

    def __init__(self, project: str, region: str, model: str) -> None:
        self.project = project
        self.region = region
        self.model = model

    async def analyze(self, prompt: str) -> str:
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
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
            response.raise_for_status()
            data = response.json()
            return data["content"][0]["text"]

    async def health_check(self) -> bool:
        try:
            self._get_access_token()
            return True
        except (FileNotFoundError, subprocess.TimeoutExpired, RuntimeError):
            return False

    def _get_access_token(self) -> str:
        result = subprocess.run(
            ["gcloud", "auth", "print-access-token"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            raise RuntimeError(f"gcloud auth failed: {result.stderr}")
        return result.stdout.strip()
