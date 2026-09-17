"""MCP-compatible cover-letter generation entry point."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from job_agent.models import Job
from job_agent.tailoring import generate_cover_letter as _generate_cover_letter


def generate_cover_letter(
    job: Job | dict[str, Any],
    master_source_path: str | Path,
    *,
    llm: object,
    prompt_version: str = "1.0.0",
) -> dict[str, Any]:
    """Generate a cover letter using an explicitly injected LLM client."""
    parsed_job = job if isinstance(job, Job) else Job.model_validate(job)
    master_source = Path(master_source_path).read_text(encoding="utf-8")
    result = _generate_cover_letter(
        parsed_job,
        master_source,
        llm,
        prompt_version=prompt_version,
    )
    return result.model_dump(mode="json")
