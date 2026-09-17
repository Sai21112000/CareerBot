from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from job_agent.snapshots import SnapshotError, save_snapshot, verify_snapshot


def _save(root: Path) -> Path:
    return save_snapshot(
        root,
        company="Example Co",
        role="AI Engineer",
        resume_tex=r"\documentclass{article}\begin{document}Resume\end{document}",
        cover_letter="Dear hiring team,\n\nSupported experience.",
        snapshot_note="# Snapshot\n\nReview before submitting.",
        source_hashes={"master_resume.tex": hashlib.sha256(b"master").hexdigest()},
        prompt_versions={"resume": "1.0.0", "cover_letter": "1.0.0"},
        model="test-model",
        source_url="https://example.com/jobs/1",
        now=datetime(2026, 9, 9, tzinfo=UTC),
    )


def test_snapshot_contains_required_files_and_valid_hashes(tmp_path: Path) -> None:
    path = _save(tmp_path)
    assert path.is_dir()
    assert {entry.name for entry in path.iterdir()} == {
        "resume.tex",
        "cover_letter.txt",
        "snapshot_note.md",
        "manifest.json",
    }

    manifest = verify_snapshot(path)
    assert manifest.snapshot_id == path.name
    assert {artifact.path for artifact in manifest.artifacts} == {
        "resume.tex",
        "cover_letter.txt",
        "snapshot_note.md",
    }
    raw_manifest = json.loads((path / "manifest.json").read_text(encoding="utf-8"))
    for artifact in raw_manifest["artifacts"]:
        content = (path / artifact["path"]).read_bytes()
        assert hashlib.sha256(content).hexdigest() == artifact["sha256"]
        assert len(content) == artifact["size"]


def test_same_inputs_create_distinct_immutable_snapshots(tmp_path: Path) -> None:
    first = _save(tmp_path)
    second = _save(tmp_path)
    assert first != second
    assert first.exists() and second.exists()
    assert not bool((first / "resume.tex").stat().st_mode & 0o222)
    assert not bool(first.stat().st_mode & 0o222)


def test_complete_package_records_inputs_and_outputs(tmp_path: Path) -> None:
    path = save_snapshot(
        tmp_path,
        company="Example Co",
        role="AI Engineer",
        resume_tex=r"\documentclass{article}\begin{document}Resume\end{document}",
        cover_letter="Evidence-backed letter.",
        cover_letter_tex=r"\documentclass{article}\begin{document}Letter\end{document}",
        resume_pdf=b"%PDF-1.4 resume",
        cover_letter_pdf=b"%PDF-1.4 letter",
        job_description="Build computer vision systems.",
        score_report={"fit_score": 90, "recommendation": "apply"},
        changes=["Moved the relevant project first."],
        submitted_answers={"work_authorization": "requires sponsorship"},
        snapshot_note="Emphasized computer vision.",
        source_hashes={"job": hashlib.sha256(b"job").hexdigest()},
        prompt_versions={"resume": "1.0.0"},
        model="test-model",
    )

    names = {entry.name for entry in path.iterdir()}
    assert {
        "resume.pdf",
        "cover_letter.tex",
        "cover_letter.pdf",
        "job_description.txt",
        "score.json",
        "changes.json",
        "submitted_answers.json",
    } <= names
    verify_snapshot(path)


def test_verification_detects_tampering(tmp_path: Path) -> None:
    path = _save(tmp_path)
    resume = path / "resume.tex"
    resume.chmod(0o644)
    resume.write_text("tampered", encoding="utf-8")
    with pytest.raises(SnapshotError, match="mismatch"):
        verify_snapshot(path)
