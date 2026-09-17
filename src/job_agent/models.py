"""Shared, serializable domain models."""

from __future__ import annotations

from datetime import UTC, date, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


def utc_now() -> datetime:
    return datetime.now(UTC)


class RoleCategory(StrEnum):
    COMPUTER_VISION = "computer vision"
    GEOSPATIAL = "geospatial"
    LLM_AGENTS = "LLM agents"
    CLOUD_AI_INFRA = "cloud/AI infra"
    OTHER = "other"


class Recommendation(StrEnum):
    APPLY = "apply"
    APPLY_WITH_CAVEATS = "apply_with_caveats"
    SKIP = "skip"


class Job(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    external_id: str | None = None
    company: str = Field(min_length=1)
    role: str = Field(min_length=1)
    description: str = Field(min_length=1)
    url: HttpUrl | None = None
    location: str | None = None
    source: str = "manual"
    discovered_at: datetime = Field(default_factory=utc_now)
    sponsorship: str | None = None
    fingerprint: str | None = None


class ScoreReport(BaseModel):
    fit_score: int = Field(ge=0, le=100)
    matched_skills: list[str]
    missing_skills: list[str]
    role_category: RoleCategory
    recommendation: Recommendation
    reasoning: str = Field(min_length=10)
    visa_or_sponsorship_flag: str | None = None
    prompt_version: str = "1.0.0"
    model: str | None = None
    source_hash: str | None = None


class TailoringResult(BaseModel):
    changes: list[str]
    tailored_tex: str
    resume_version_note: str
    prompt_version: str = "1.0.0"


class CoverLetterResult(BaseModel):
    body: str
    prompt_version: str = "1.0.0"


class ArtifactHash(BaseModel):
    path: str
    sha256: str
    size: int


class SnapshotManifest(BaseModel):
    snapshot_id: str
    created_at: datetime = Field(default_factory=utc_now)
    company: str
    role: str
    source_url: str | None = None
    source_hashes: dict[str, str]
    prompt_versions: dict[str, str]
    model: str
    artifacts: list[ArtifactHash]
    status: str = "prepared"


class ApplicationStatus(StrEnum):
    PREPARED = "prepared"
    READY = "ready"
    SUBMITTING = "submitting"
    SUBMITTED = "submitted"
    HANDOFF = "handoff"
    FAILED = "failed"


class ApplicationRecord(BaseModel):
    idempotency_key: str
    date_applied: date | None = None
    company: str
    role: str
    job_url: str | None = None
    snapshot_path: Path
    resume_version_note: str
    status: ApplicationStatus = ApplicationStatus.PREPARED
    applied_via: str | None = None
    follow_up_date: date | None = None
    confirmation_id: str | None = None
    submitted_answers: dict[str, Any] = Field(default_factory=dict)
    updated_at: datetime = Field(default_factory=utc_now)


class Handoff(BaseModel):
    reason: str
    url: str | None = None
    required_actions: list[str]
    created_at: datetime = Field(default_factory=utc_now)


class RunManifest(BaseModel):
    run_id: str
    started_at: datetime = Field(default_factory=utc_now)
    completed_at: datetime | None = None
    profile: str
    jobs_seen: int = 0
    applications_prepared: int = 0
    applications_submitted: int = 0
    handoffs: int = 0
    errors: list[str] = Field(default_factory=list)
