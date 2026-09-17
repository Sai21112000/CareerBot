"""MCP-callable bounded job discovery operation."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from job_agent.discovery import EmailAlertSource, JobSource, ManualSource, discover_jobs
from job_agent.models import Job


def search_jobs(
    query: str,
    *,
    limit: int = 20,
    sources: Iterable[JobSource] = (),
    manual_jobs: Iterable[Job | Mapping[str, Any]] = (),
    email_alerts: Iterable[Mapping[str, str]] = (),
) -> list[dict[str, Any]]:
    """Search only explicitly supplied, automation-permitted sources."""
    jobs = [
        item if isinstance(item, Job) else Job.model_validate(item)
        for item in manual_jobs
    ]
    configured: list[JobSource] = list(sources)
    if jobs:
        configured.append(ManualSource(jobs))
    alerts = list(email_alerts)
    if alerts:
        configured.append(EmailAlertSource(alerts))
    return [
        job.model_dump(mode="json")
        for job in discover_jobs(configured, query, limit=limit)
    ]
