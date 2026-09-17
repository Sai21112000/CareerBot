"""MCP-compatible resume tailoring entry point."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from job_agent.models import Job
from job_agent.tailoring import tailor_resume as _tailor_resume


def tailor_resume(
    job: Job | dict[str, Any],
    master_resume_path: str | Path,
    *,
    llm: object,
    prompt_version: str = "1.0.0",
    compilation_output_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Tailor a resume using an explicitly injected LLM client."""
    parsed_job = job if isinstance(job, Job) else Job.model_validate(job)
    master_tex = Path(master_resume_path).read_text(encoding="utf-8")
    result = _tailor_resume(
        parsed_job,
        master_tex,
        llm,
        prompt_version=prompt_version,
        compilation_output_dir=(
            Path(compilation_output_dir) if compilation_output_dir is not None else None
        ),
    )
    payload = result.model_dump(mode="json")
    if compilation_output_dir is not None:
        pdf_path = Path(compilation_output_dir) / "resume.pdf"
        payload["resume_pdf_path"] = str(pdf_path) if pdf_path.is_file() else None
    return payload
