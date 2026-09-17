from __future__ import annotations

import json

import httpx
import pytest

from job_agent.xai_client import XAIClient, XAITextClient


@pytest.mark.asyncio
async def test_async_xai_client_uses_responses_api() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/responses"
        payload = json.loads(request.content)
        assert payload["text"]["format"]["type"] == "json_schema"
        return httpx.Response(
            200,
            json={
                "output": [
                    {
                        "content": [
                            {
                                "text": json.dumps(
                                    {
                                        "fit_score": 90,
                                        "matched_skills": ["Python"],
                                        "missing_skills": [],
                                        "role_category": "computer vision",
                                        "recommendation": "apply",
                                        "reasoning": "Strong verified overlap with the role.",
                                    }
                                )
                            }
                        ]
                    }
                ]
            },
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(
        base_url="https://api.x.ai/v1",
        transport=transport,
    ) as http_client:
        client = XAIClient("test", http_client=http_client)
        output = await client.generate_score(prompt="prompt", job={"company": "Acme"})
    assert isinstance(output, str)
    assert json.loads(output)["fit_score"] == 90


def test_sync_xai_text_client_extracts_output_text() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/responses"
        return httpx.Response(200, json={"output_text": "generated text"})

    http_client = httpx.Client(
        base_url="https://api.x.ai/v1",
        transport=httpx.MockTransport(handler),
    )
    with http_client:
        client = XAITextClient("test", http_client=http_client)
        assert client("prompt") == "generated text"
