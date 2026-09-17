"""MCP-facing job scoring tool."""

from __future__ import annotations

from job_agent.config import Settings
from job_agent.models import Job, ScoreReport
from job_agent.scoring import score_job as score_job_core
from job_agent.xai_client import ScoreClient, XAIClient


async def score_job(
    job: Job,
    *,
    client: ScoreClient | None = None,
    settings: Settings | None = None,
) -> ScoreReport:
    """Score a job with an injected client or the configured xAI client."""

    if client is not None:
        return await score_job_core(job, client)

    runtime = settings or Settings()
    if runtime.xai_api_key is None:
        raise ValueError("CAREERBOT_XAI_API_KEY is required to score a job")

    async with XAIClient(
        runtime.xai_api_key.get_secret_value(),
        model=runtime.xai_model,
    ) as xai:
        return await score_job_core(job, xai)
