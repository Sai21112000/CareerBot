"""Command-line entry point for bounded local CareerBot sessions."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import tempfile
import time
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from job_agent.config import ExecutionProfile, Settings
from job_agent.discovery import ManualSource, discover_jobs
from job_agent.latex import compile_latex, compile_one_page_resume, cover_letter_document
from job_agent.models import ApplicationRecord, Job
from job_agent.scoring import load_master_cv_text, score_job, source_hash
from job_agent.snapshots import save_snapshot, verify_snapshot
from job_agent.strategy import CareerStrategyStore, strategy_context
from job_agent.tailoring import generate_cover_letter, tailor_resume
from job_agent.tracking import CSVApplicationStore
from job_agent.xai_client import XAIClient, XAITextClient


def _json_file(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _print(value: object) -> None:
    print(json.dumps(value, indent=2, sort_keys=True, default=str))


async def _score(parsed_job: Job, settings: Settings) -> dict[str, Any]:
    if settings.xai_api_key is None:
        raise RuntimeError("Set CAREERBOT_XAI_API_KEY before using model-backed commands")
    async with XAIClient(
        settings.xai_api_key.get_secret_value(),
        model=settings.xai_model,
    ) as client:
        approved_strategy = CareerStrategyStore(
            settings.career_strategy_path,
            settings.strategy_snapshot_dir,
        ).load()
        report = await score_job(
            parsed_job,
            client,
            master_cv_text=load_master_cv_text(settings.data_dir / "master_cv"),
            career_strategy_context=strategy_context(approved_strategy),
        )
    return report.model_dump(mode="json")


def _triage(args: argparse.Namespace, settings: Settings) -> None:
    payload = _json_file(args.input)
    raw_jobs = payload.get("jobs", payload) if isinstance(payload, dict) else payload
    jobs = [Job.model_validate(item) for item in raw_jobs]
    limit = min(args.max_jobs or settings.max_jobs_per_run, settings.max_jobs_per_run)
    approved_strategy = CareerStrategyStore(
        settings.career_strategy_path,
        settings.strategy_snapshot_dir,
    ).load()
    target_terms = approved_strategy.target_terms() if approved_strategy else ()
    ranked = discover_jobs(
        [ManualSource(jobs)],
        args.query,
        limit=limit,
        **({"target_terms": target_terms} if target_terms else {}),
    )
    _print([job.model_dump(mode="json") for job in ranked])


def _apply(args: argparse.Namespace, settings: Settings) -> None:
    job = Job.model_validate(_json_file(args.job))
    if not settings.master_resume_path.is_file():
        raise RuntimeError("Install your verified resume at data/master_resume.tex")
    master_tex = settings.master_resume_path.read_text(encoding="utf-8")
    score = asyncio.run(_score(job, settings))
    assert settings.xai_api_key is not None
    with XAITextClient(
        settings.xai_api_key.get_secret_value(),
        model=settings.xai_model,
    ) as llm:
        tailored = tailor_resume(job, master_tex, llm)
        letter = generate_cover_letter(job, tailored.tailored_tex, llm)

    letter_tex = cover_letter_document(letter.body)
    with tempfile.TemporaryDirectory(prefix="careerbot-apply-") as temporary:
        output = Path(temporary)
        resume_build = compile_one_page_resume(tailored.tailored_tex, output, stem="resume")
        letter_build = compile_latex(
            letter_tex,
            output,
            stem="cover_letter",
            require_one_page=True,
        )
        snapshot = save_snapshot(
            settings.snapshot_dir,
            company=job.company,
            role=job.role,
            resume_tex=tailored.tailored_tex,
            cover_letter=letter.body,
            snapshot_note=tailored.resume_version_note,
            source_hashes={"job": source_hash(job), "master_resume": _sha256_text(master_tex)},
            prompt_versions={
                "scoring": str(score.get("prompt_version", "1.0.0")),
                "resume": tailored.prompt_version,
                "cover_letter": letter.prompt_version,
            },
            model=settings.xai_model,
            source_url=str(job.url) if job.url else None,
            resume_pdf=resume_build.pdf_path,
            cover_letter_tex=letter_tex,
            cover_letter_pdf=letter_build.pdf_path,
            job_description=job.description,
            score_report=score,
            changes=tailored.changes,
        )

    record = ApplicationRecord(
        idempotency_key=source_hash(job),
        company=job.company,
        role=job.role,
        job_url=str(job.url) if job.url else None,
        snapshot_path=snapshot,
        resume_version_note=tailored.resume_version_note,
        applied_via=job.source,
        follow_up_date=date.today() + timedelta(days=7),
    )
    CSVApplicationStore(settings.application_log_path).upsert(record)
    _print(
        {
            "profile": settings.execution_profile,
            "score": score,
            "snapshot_path": str(snapshot),
            "snapshot_verified": verify_snapshot(snapshot).snapshot_id,
            "status": record.status,
            "next_action": (
                "Review the package before submission."
                if settings.execution_profile is not ExecutionProfile.AUTO
                else "Prepared; no authorized submission connector was configured."
            ),
        }
    )


def _batch_apply(args: argparse.Namespace, settings: Settings) -> None:
    payload = _json_file(args.queue)
    raw_jobs = payload.get("jobs", payload) if isinstance(payload, dict) else payload
    jobs = [Job.model_validate(item) for item in raw_jobs]
    existing = {
        item.idempotency_key
        for item in CSVApplicationStore(settings.application_log_path).read_all()
    }
    maximum = min(args.max_applications, settings.max_applications_per_run)
    deadline = time.monotonic() + min(args.max_minutes, settings.max_run_minutes) * 60
    prepared = 0
    skipped: list[str] = []
    for job in jobs:
        key = source_hash(job)
        if key in existing:
            skipped.append(key)
            continue
        if prepared >= maximum or time.monotonic() >= deadline:
            break
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", encoding="utf-8") as source:
            source.write(job.model_dump_json())
            source.flush()
            _apply(argparse.Namespace(job=source.name), settings)
        existing.add(key)
        prepared += 1
    _print({"prepared": prepared, "skipped_existing": skipped, "bounded": True})


def _sha256_text(value: str) -> str:
    import hashlib

    return hashlib.sha256(value.encode()).hexdigest()


def _follow_up(args: argparse.Namespace, settings: Settings) -> None:
    records = CSVApplicationStore(settings.application_log_path).read_all()
    due = [
        item.model_dump(mode="json")
        for item in records
        if item.follow_up_date is not None and item.follow_up_date <= date.today()
    ][: args.limit]
    _print({"due": due, "count": len(due), "external_writes": 0})


def _reconcile(args: argparse.Namespace, settings: Settings) -> None:
    records = CSVApplicationStore(settings.application_log_path).read_all()[: args.limit]
    _print(
        {
            "local_records": len(records),
            "airtable_configured": bool(settings.airtable_pat and settings.airtable_base_id),
            "note": "Use the Airtable-backed MCP tracker for remote upserts.",
        }
    )


def _verify(args: argparse.Namespace, _settings: Settings) -> None:
    _print(verify_snapshot(Path(args.snapshot)).model_dump(mode="json"))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="careerbot")
    parser.add_argument(
        "--profile",
        choices=[item.value for item in ExecutionProfile],
        help="Override CAREERBOT_EXECUTION_PROFILE",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    triage = commands.add_parser("triage", help="Rank and deduplicate supplied jobs")
    triage.add_argument("--input", required=True)
    triage.add_argument("--query", default="")
    triage.add_argument("--max-jobs", type=int)
    triage.add_argument("--max-minutes", type=int, help="Reserved bounded-run contract")
    triage.set_defaults(handler=_triage)

    apply_command = commands.add_parser("apply", help="Prepare an immutable application package")
    apply_command.add_argument("--job", required=True)
    apply_command.set_defaults(handler=_apply)

    batch = commands.add_parser("batch-apply", help="Prepare a bounded resumable job batch")
    batch.add_argument("--queue", required=True)
    batch.add_argument("--max-applications", type=int, default=5)
    batch.add_argument("--max-minutes", type=int, default=30)
    batch.set_defaults(handler=_batch_apply)

    follow_up = commands.add_parser("follow-up", help="List due follow-ups")
    follow_up.add_argument("action", choices=["sync"])
    follow_up.add_argument("--limit", type=int, default=20)
    follow_up.add_argument("--max-minutes", type=int)
    follow_up.set_defaults(handler=_follow_up)

    reconcile = commands.add_parser("reconcile", help="Report local/Airtable readiness")
    reconcile.add_argument("--limit", type=int, default=50)
    reconcile.add_argument("--max-minutes", type=int)
    reconcile.set_defaults(handler=_reconcile)

    verify = commands.add_parser("verify-snapshot", help="Verify immutable artifact hashes")
    verify.add_argument("snapshot")
    verify.set_defaults(handler=_verify)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    settings = Settings(
        execution_profile=args.profile or Settings().execution_profile,
    )
    try:
        args.handler(args, settings)
    except Exception as exc:
        print(f"careerbot: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
