"""Immutable, content-addressed artifact snapshots."""

from __future__ import annotations

import hashlib
import json
import os
import secrets
import shutil
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path

from slugify import slugify

from job_agent.models import ArtifactHash, SnapshotManifest

REQUIRED_ARTIFACTS = ("resume.tex", "cover_letter.txt", "snapshot_note.md")
MANIFEST_NAME = "manifest.json"


class SnapshotError(RuntimeError):
    """Raised when a snapshot cannot be created or verified."""


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _artifact_hash(path: Path, root: Path) -> ArtifactHash:
    return ArtifactHash(
        path=path.relative_to(root).as_posix(),
        sha256=sha256_file(path),
        size=path.stat().st_size,
    )


def _snapshot_id(company: str, role: str, now: datetime, nonce: str) -> str:
    label = slugify(f"{company}-{role}", max_length=64) or "application"
    timestamp = now.astimezone(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    return f"{timestamp}-{label}-{nonce}"


def save_snapshot(
    snapshot_dir: Path,
    *,
    company: str,
    role: str,
    resume_tex: str,
    cover_letter: str,
    snapshot_note: str,
    source_hashes: Mapping[str, str],
    prompt_versions: Mapping[str, str],
    model: str,
    source_url: str | None = None,
    resume_pdf: bytes | Path | None = None,
    cover_letter_tex: str | None = None,
    cover_letter_pdf: bytes | Path | None = None,
    job_description: str | None = None,
    score_report: Mapping[str, object] | None = None,
    changes: list[str] | None = None,
    submitted_answers: Mapping[str, object] | None = None,
    status: str = "prepared",
    now: datetime | None = None,
) -> Path:
    """Atomically create a new snapshot and never overwrite an existing one."""
    if not company.strip() or not role.strip():
        raise SnapshotError("company and role are required")
    if not resume_tex.strip() or not cover_letter.strip() or not snapshot_note.strip():
        raise SnapshotError("resume, cover letter, and snapshot note are required")
    if not source_hashes:
        raise SnapshotError("at least one source hash is required")
    if not prompt_versions:
        raise SnapshotError("at least one prompt version is required")
    if not model.strip():
        raise SnapshotError("model is required")

    root = Path(snapshot_dir)
    root.mkdir(parents=True, exist_ok=True)
    created_at = now or datetime.now(UTC)

    for attempt in range(20):
        nonce = f"{secrets.token_hex(4)}-{attempt:02d}"
        snapshot_id = _snapshot_id(company, role, created_at, nonce)
        destination = root / snapshot_id
        if not destination.exists():
            break
    else:
        raise SnapshotError("unable to allocate a collision-free snapshot id")

    staging = root / f".{snapshot_id}.tmp-{secrets.token_hex(4)}"
    try:
        staging.mkdir(mode=0o700)
        (staging / "resume.tex").write_text(resume_tex, encoding="utf-8")
        (staging / "cover_letter.txt").write_text(cover_letter, encoding="utf-8")
        (staging / "snapshot_note.md").write_text(snapshot_note, encoding="utf-8")
        if cover_letter_tex is not None:
            (staging / "cover_letter.tex").write_text(cover_letter_tex, encoding="utf-8")
        if job_description is not None:
            (staging / "job_description.txt").write_text(job_description, encoding="utf-8")
        if score_report is not None:
            (staging / "score.json").write_text(
                json.dumps(dict(score_report), indent=2, sort_keys=True, default=str) + "\n",
                encoding="utf-8",
            )
        if changes is not None:
            (staging / "changes.json").write_text(
                json.dumps(changes, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
        if submitted_answers is not None:
            (staging / "submitted_answers.json").write_text(
                json.dumps(dict(submitted_answers), indent=2, sort_keys=True, default=str) + "\n",
                encoding="utf-8",
            )
        if isinstance(resume_pdf, Path):
            shutil.copyfile(resume_pdf, staging / "resume.pdf")
        elif isinstance(resume_pdf, bytes):
            (staging / "resume.pdf").write_bytes(resume_pdf)
        elif resume_pdf is not None:
            raise TypeError("resume_pdf must be bytes, Path, or None")
        if isinstance(cover_letter_pdf, Path):
            shutil.copyfile(cover_letter_pdf, staging / "cover_letter.pdf")
        elif isinstance(cover_letter_pdf, bytes):
            (staging / "cover_letter.pdf").write_bytes(cover_letter_pdf)
        elif cover_letter_pdf is not None:
            raise TypeError("cover_letter_pdf must be bytes, Path, or None")

        artifact_paths = sorted(
            path for path in staging.iterdir() if path.is_file() and path.name != MANIFEST_NAME
        )
        artifacts = [_artifact_hash(path, staging) for path in artifact_paths]
        manifest = SnapshotManifest(
            snapshot_id=snapshot_id,
            created_at=created_at,
            company=company,
            role=role,
            source_url=source_url,
            source_hashes=dict(source_hashes),
            prompt_versions=dict(prompt_versions),
            model=model,
            artifacts=artifacts,
            status=status,
        )
        manifest_path = staging / MANIFEST_NAME
        manifest_path.write_text(
            json.dumps(manifest.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        os.rename(staging, destination)
        for path in destination.iterdir():
            path.chmod(0o444)
        destination.chmod(0o555)
        return destination
    except Exception:
        if staging.exists():
            shutil.rmtree(staging)
        raise


def load_manifest(snapshot_path: Path) -> SnapshotManifest:
    try:
        content = (Path(snapshot_path) / MANIFEST_NAME).read_text(encoding="utf-8")
        return SnapshotManifest.model_validate_json(content)
    except (OSError, ValueError) as exc:
        raise SnapshotError(f"invalid snapshot manifest: {exc}") from exc


def verify_snapshot(snapshot_path: Path) -> SnapshotManifest:
    """Verify required files, paths, sizes, and SHA-256 hashes."""
    root = Path(snapshot_path)
    manifest = load_manifest(root)
    if root.name != manifest.snapshot_id:
        raise SnapshotError("snapshot directory does not match manifest snapshot_id")

    recorded = {artifact.path: artifact for artifact in manifest.artifacts}
    missing = [name for name in REQUIRED_ARTIFACTS if name not in recorded]
    if missing:
        raise SnapshotError(f"manifest omits required artifacts: {', '.join(missing)}")

    for relative, artifact in recorded.items():
        candidate = (root / relative).resolve()
        try:
            candidate.relative_to(root.resolve())
        except ValueError as exc:
            raise SnapshotError(f"artifact path escapes snapshot: {relative}") from exc
        if not candidate.is_file():
            raise SnapshotError(f"artifact is missing: {relative}")
        if candidate.stat().st_size != artifact.size:
            raise SnapshotError(f"artifact size mismatch: {relative}")
        if sha256_file(candidate) != artifact.sha256:
            raise SnapshotError(f"artifact hash mismatch: {relative}")
    return manifest
