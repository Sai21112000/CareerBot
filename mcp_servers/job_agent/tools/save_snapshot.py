"""MCP-compatible immutable snapshot entry point."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from job_agent.snapshots import save_snapshot as _save_snapshot
from job_agent.snapshots import verify_snapshot


def save_snapshot(
    snapshot_dir: str | Path,
    *,
    company: str,
    role: str,
    resume_tex: str,
    cover_letter: str,
    snapshot_note: str,
    source_hashes: dict[str, str],
    prompt_versions: dict[str, str],
    model: str,
    source_url: str | None = None,
    resume_pdf_path: str | Path | None = None,
    cover_letter_tex: str | None = None,
    cover_letter_pdf_path: str | Path | None = None,
    job_description: str | None = None,
    score_report: dict[str, object] | None = None,
    changes: list[str] | None = None,
    submitted_answers: dict[str, object] | None = None,
    status: str = "prepared",
) -> dict[str, Any]:
    """Persist and immediately verify a collision-safe immutable snapshot."""
    pdf = Path(resume_pdf_path) if resume_pdf_path is not None else None
    letter_pdf = Path(cover_letter_pdf_path) if cover_letter_pdf_path is not None else None
    path = _save_snapshot(
        Path(snapshot_dir),
        company=company,
        role=role,
        resume_tex=resume_tex,
        cover_letter=cover_letter,
        snapshot_note=snapshot_note,
        source_hashes=source_hashes,
        prompt_versions=prompt_versions,
        model=model,
        source_url=source_url,
        resume_pdf=pdf,
        cover_letter_tex=cover_letter_tex,
        cover_letter_pdf=letter_pdf,
        job_description=job_description,
        score_report=score_report,
        changes=changes,
        submitted_answers=submitted_answers,
        status=status,
    )
    manifest = verify_snapshot(path)
    return {
        "snapshot_path": str(path),
        "manifest": manifest.model_dump(mode="json"),
    }
