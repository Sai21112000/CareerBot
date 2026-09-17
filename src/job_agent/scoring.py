"""Job normalization, deduplication, and structured scoring."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from job_agent.models import Job, Recommendation, ScoreReport
from job_agent.xai_client import ScoreClient

PROMPT_VERSION = "1.0.0"
_PROMPT_PATH = Path(__file__).with_name("prompts") / "scoring_prompt.md"
_WHITESPACE = re.compile(r"\s+")
_NO_SPONSORSHIP = re.compile(
    r"\b(?:no|not offering|unable to (?:offer|provide))\s+(?:visa\s+)?sponsorship\b",
    re.IGNORECASE,
)
_EXISTING_AUTHORIZATION = re.compile(
    r"\b(?:must|need to)\s+(?:already\s+)?(?:be\s+)?(?:legally\s+)?"
    r"(?:authorized|eligible)\s+to\s+work\b",
    re.IGNORECASE,
)
_THAILAND_LOCATION = re.compile(r"\b(?:thailand|bangkok)\b", re.IGNORECASE)
_REMOTE_ANYWHERE = re.compile(
    r"\b(?:remote\s*(?:worldwide|anywhere|global)|work from anywhere)\b",
    re.IGNORECASE,
)


def normalize_text(value: str | None) -> str:
    """Return stable text for hashing and comparison."""

    return _WHITESPACE.sub(" ", value or "").strip().casefold()


def normalized_job(job: Job) -> dict[str, str]:
    """Return the source fields that define a stable job posting."""

    return {
        "company": normalize_text(job.company),
        "role": normalize_text(job.role),
        "description": normalize_text(job.description),
        "url": normalize_text(str(job.url) if job.url else None),
        "location": normalize_text(job.location),
        "source": normalize_text(job.source),
        "sponsorship": normalize_text(job.sponsorship),
    }


_TEXT_SUFFIXES = {".md", ".txt", ".tex"}


def load_master_cv_text(path: Path) -> str:
    """Load verified text-like CV sources and hash-pinned source manifests.

    Manifest entries are the authoritative, hash-verified load path. Their paths are
    resolved relative to the manifest so the project stays self-contained, and any file
    also present in the directory glob is skipped to avoid counting it twice.
    """
    if path.is_file():
        return path.read_text(encoding="utf-8")
    if not path.is_dir():
        return ""

    parts: list[str] = []
    manifest_paths: set[Path] = set()
    manifest_path = path / "sources.json"
    if manifest_path.is_file():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        for entry in manifest.get("sources", []):
            source = Path(entry["path"])
            if not source.is_absolute():
                source = manifest_path.parent / source
            manifest_paths.add(source.resolve())
            content = source.read_bytes()
            actual_hash = hashlib.sha256(content).hexdigest()
            if actual_hash != entry["sha256"]:
                raise ValueError(f"master CV source hash changed: {source}")
            if source.suffix.casefold() in _TEXT_SUFFIXES:
                parts.append(content.decode("utf-8"))

    for source in sorted(path.rglob("*")):
        if source.resolve() in manifest_paths:
            continue
        if source.is_file() and source.suffix.casefold() in _TEXT_SUFFIXES:
            parts.append(source.read_text(encoding="utf-8"))
    return "\n\n".join(parts)


def source_hash(job: Job) -> str:
    """Hash normalized source content, excluding discovery metadata."""

    payload = json.dumps(
        normalized_job(job),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def fingerprint_job(job: Job) -> str:
    """Create a deduplication fingerprint for the posting."""

    identity = {
        "company": normalize_text(job.company),
        "external_id": normalize_text(job.external_id),
        "role": normalize_text(job.role),
        "url": normalize_text(str(job.url) if job.url else None),
    }
    payload = json.dumps(identity, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def deduplicate_jobs(jobs: Iterable[Job]) -> list[Job]:
    """Keep the first job for each fingerprint and attach its fingerprint."""

    unique: list[Job] = []
    seen: set[str] = set()
    for job in jobs:
        fingerprint = job.fingerprint or fingerprint_job(job)
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        unique.append(job.model_copy(update={"fingerprint": fingerprint}))
    return unique


def validate_score_output(output: Mapping[str, Any] | str) -> ScoreReport:
    """Validate model output against the shared structured score model."""

    if isinstance(output, str):
        return ScoreReport.model_validate_json(output)
    return ScoreReport.model_validate(output)


def apply_deterministic_rules(job: Job, report: ScoreReport) -> ScoreReport:
    """Apply visa and location constraints after model scoring."""

    evidence = " ".join(
        part for part in (job.sponsorship, job.location, job.description) if part
    )
    no_sponsorship = bool(_NO_SPONSORSHIP.search(evidence))
    requires_existing_auth = bool(_EXISTING_AUTHORIZATION.search(evidence))
    local_or_global = bool(
        _THAILAND_LOCATION.search(job.location or "")
        or _REMOTE_ANYWHERE.search(job.location or "")
        or _REMOTE_ANYWHERE.search(job.description)
    )

    if no_sponsorship or (requires_existing_auth and not local_or_global):
        reason = (
            "Employer explicitly states that visa sponsorship is unavailable."
            if no_sponsorship
            else "Role requires existing work authorization outside Thailand."
        )
        return report.model_copy(
            update={
                "fit_score": min(report.fit_score, 39),
                "recommendation": Recommendation.SKIP,
                "visa_or_sponsorship_flag": reason,
            }
        )
    return report


async def score_job(
    job: Job,
    client: ScoreClient,
    *,
    master_cv_text: str = "",
    career_strategy_context: str = "",
    validation_attempts: int = 2,
) -> ScoreReport:
    """Score one job, retrying once when model output is malformed."""

    if validation_attempts < 1:
        raise ValueError("validation_attempts must be at least 1")

    prompt = _PROMPT_PATH.read_text(encoding="utf-8")
    payload = normalized_job(job)
    payload["master_cv_text"] = master_cv_text.strip()
    payload["career_strategy_context"] = career_strategy_context.strip()
    last_error: ValidationError | None = None

    for _ in range(validation_attempts):
        output = await client.generate_score(prompt=prompt, job=payload)
        try:
            report = validate_score_output(output)
        except ValidationError as exc:
            last_error = exc
            continue
        report = report.model_copy(
            update={
                "prompt_version": PROMPT_VERSION,
                "model": client.model,
                "source_hash": source_hash(job),
            }
        )
        return apply_deterministic_rules(job, report)

    if last_error is not None:
        raise last_error
    raise RuntimeError("Scoring failed without producing output")
