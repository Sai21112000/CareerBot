from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pytest
from pydantic import ValidationError

from job_agent.models import Job, Recommendation
from job_agent.scoring import (
    deduplicate_jobs,
    fingerprint_job,
    score_job,
    source_hash,
)


class FakeScoreClient:
    def __init__(self, outputs: list[Mapping[str, Any] | str]) -> None:
        self.outputs = iter(outputs)
        self.calls = 0
        self.jobs: list[Mapping[str, str]] = []

    @property
    def model(self) -> str:
        return "fake-model"

    async def generate_score(
        self,
        *,
        prompt: str,
        job: Mapping[str, str],
    ) -> Mapping[str, Any] | str:
        assert "conservative job-fit evaluator" in prompt
        assert job["company"]
        self.calls += 1
        self.jobs.append(job)
        return next(self.outputs)


def model_output(
    *,
    score: int,
    recommendation: str,
    category: str = "computer vision",
) -> dict[str, Any]:
    return {
        "fit_score": score,
        "matched_skills": ["Python", "computer vision"],
        "missing_skills": [],
        "role_category": category,
        "recommendation": recommendation,
        "reasoning": "The role has clear overlap with the candidate's demonstrated experience.",
        "visa_or_sponsorship_flag": None,
    }


@pytest.mark.asyncio
async def test_scores_high_fit_job() -> None:
    job = Job(
        company="Vision Co",
        role="Computer Vision Engineer",
        location="Bangkok, Thailand",
        description="Build Python instance-segmentation models for satellite imagery.",
    )
    client = FakeScoreClient([model_output(score=91, recommendation="apply")])

    report = await score_job(job, client)

    assert report.fit_score == 91
    assert report.recommendation is Recommendation.APPLY
    assert report.model == "fake-model"
    assert report.source_hash == source_hash(job)


@pytest.mark.asyncio
async def test_scoring_receives_approved_strategy_as_priority_context() -> None:
    job = Job(
        company="AI Co",
        role="Applied AI Engineer",
        description="Build governed AI agents.",
    )
    client = FakeScoreClient([model_output(score=88, recommendation="apply")])

    await score_job(
        job,
        client,
        master_cv_text="Verified agent experience.",
        career_strategy_context='{"primary_target_roles":["Applied AI Engineer"]}',
    )

    assert client.jobs[0]["master_cv_text"] == "Verified agent experience."
    assert "Applied AI Engineer" in client.jobs[0]["career_strategy_context"]


@pytest.mark.asyncio
async def test_scores_weak_fit_job() -> None:
    job = Job(
        company="Ledger Co",
        role="Senior Accountant",
        location="Bangkok",
        description="Lead statutory accounting, tax, and audit work.",
    )
    client = FakeScoreClient(
        [
            {
                **model_output(
                    score=24,
                    recommendation="skip",
                    category="other",
                ),
                "matched_skills": [],
                "missing_skills": ["statutory accounting", "tax"],
            }
        ]
    )

    report = await score_job(job, client)

    assert report.fit_score == 24
    assert report.recommendation is Recommendation.SKIP


@pytest.mark.asyncio
async def test_explicit_sponsorship_mismatch_overrides_model() -> None:
    job = Job(
        company="Remote AI",
        role="ML Engineer",
        location="San Francisco, USA",
        sponsorship="No visa sponsorship is available.",
        description="Develop computer vision models with Python.",
    )
    client = FakeScoreClient([model_output(score=94, recommendation="apply")])

    report = await score_job(job, client)

    assert report.fit_score == 39
    assert report.recommendation is Recommendation.SKIP
    assert report.visa_or_sponsorship_flag is not None
    assert "unavailable" in report.visa_or_sponsorship_flag


@pytest.mark.asyncio
async def test_malformed_output_is_retried_then_rejected() -> None:
    job = Job(company="AI Co", role="Engineer", description="Build AI products.")
    malformed = {"fit_score": 120, "reasoning": "too short"}
    client = FakeScoreClient([malformed, malformed])

    with pytest.raises(ValidationError):
        await score_job(job, client)

    assert client.calls == 2


def test_source_hash_normalizes_whitespace_and_ignores_discovery_time() -> None:
    first = Job(
        company="Example AI",
        role="ML Engineer",
        description="Build   robust\nmodels.",
        location=" Bangkok ",
    )
    equivalent = Job(
        company=" example ai ",
        role="ml engineer",
        description="build robust models.",
        location="bangkok",
    )
    changed = equivalent.model_copy(update={"description": "Build language models."})

    assert source_hash(first) == source_hash(equivalent)
    assert source_hash(first) != source_hash(changed)
    assert len(source_hash(first)) == 64


def test_fingerprint_and_deduplication_are_stable() -> None:
    first = Job(
        company="Example AI",
        role="ML Engineer",
        description="Original description.",
        url="https://example.com/jobs/1",
    )
    duplicate = first.model_copy(update={"description": "Updated description."})

    jobs = deduplicate_jobs([first, duplicate])

    assert len(jobs) == 1
    assert jobs[0].fingerprint == fingerprint_job(first)
