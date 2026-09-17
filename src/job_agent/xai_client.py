"""Small, injectable xAI Responses API clients."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from typing import Any, Protocol

import httpx

from job_agent.models import ScoreReport


class ScoreClient(Protocol):
    """Interface used by scoring and easily implemented by test fakes."""

    @property
    def model(self) -> str: ...

    async def generate_score(
        self,
        *,
        prompt: str,
        job: Mapping[str, str],
    ) -> Mapping[str, Any] | str: ...


class XAIClient:
    """Async xAI Responses API client with bounded transient retries."""

    def __init__(
        self,
        api_key: str,
        *,
        model: str = "grok-4.6",
        base_url: str = "https://api.x.ai/v1",
        timeout_seconds: float = 30.0,
        max_attempts: int = 3,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        if not api_key:
            raise ValueError("api_key must not be empty")
        if max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        self._model = model
        self._max_attempts = max_attempts
        self._owns_client = http_client is None
        self._client = http_client or httpx.AsyncClient(
            base_url=base_url,
            timeout=timeout_seconds,
            headers={"Authorization": f"Bearer {api_key}"},
        )

    @property
    def model(self) -> str:
        return self._model

    async def generate_score(
        self,
        *,
        prompt: str,
        job: Mapping[str, str],
    ) -> Mapping[str, Any] | str:
        request = {
            "model": self.model,
            "input": [
                {"role": "system", "content": prompt},
                {"role": "user", "content": "Score this normalized job:\n"
                 + "\n".join(f"{key}: {value}" for key, value in job.items())},
            ],
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "score_report",
                    "strict": True,
                    "schema": ScoreReport.model_json_schema(),
                }
            },
        }

        for attempt in range(1, self._max_attempts + 1):
            try:
                response = await self._client.post("/responses", json=request)
                response.raise_for_status()
            except (httpx.TimeoutException, httpx.NetworkError, httpx.RemoteProtocolError):
                if attempt == self._max_attempts:
                    raise
                await asyncio.sleep(0.25 * 2 ** (attempt - 1))
                continue
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code not in {408, 409, 429, 500, 502, 503, 504}:
                    raise
                if attempt == self._max_attempts:
                    raise
                await asyncio.sleep(0.25 * 2 ** (attempt - 1))
                continue

            return _responses_text(response.json())

        raise RuntimeError("xAI request exhausted retries")

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def __aenter__(self) -> XAIClient:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: object | None,
    ) -> None:
        await self.aclose()


def _responses_text(body: Any) -> str:
    """Extract text from Responses API output across SDK-compatible shapes."""
    if isinstance(body, dict):
        direct = body.get("output_text")
        if isinstance(direct, str):
            return direct
        for item in body.get("output", []):
            if not isinstance(item, dict):
                continue
            for content in item.get("content", []):
                if not isinstance(content, dict):
                    continue
                text = content.get("text")
                if isinstance(text, str):
                    return text
    raise ValueError("xAI response did not contain output text")


class XAITextClient:
    """Synchronous callable used by tailoring and cover-letter generation."""

    def __init__(
        self,
        api_key: str,
        *,
        model: str = "grok-4.6",
        base_url: str = "https://api.x.ai/v1",
        timeout_seconds: float = 60.0,
        http_client: httpx.Client | None = None,
    ) -> None:
        if not api_key:
            raise ValueError("api_key must not be empty")
        self.model = model
        self._owns_client = http_client is None
        self._client = http_client or httpx.Client(
            base_url=base_url,
            timeout=timeout_seconds,
            headers={"Authorization": f"Bearer {api_key}"},
        )

    def __call__(self, prompt: str) -> str:
        response = self._client.post(
            "/responses",
            json={"model": self.model, "input": prompt},
        )
        response.raise_for_status()
        return _responses_text(response.json())

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> XAITextClient:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
