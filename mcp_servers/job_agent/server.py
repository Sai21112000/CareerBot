"""CareerBot MCP composition root.

Stdio is intended for trusted local use. Remote HTTP refuses to start without a bearer
token and should be placed behind HTTPS in production.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any

from fastmcp import FastMCP
from fastmcp.server.auth.providers.jwt import StaticTokenVerifier

from job_agent.airtable import AirtableClient
from job_agent.config import Settings
from job_agent.discovery import EmailAlertSource, JobSource, ManualSource, discover_jobs
from job_agent.latex import compile_latex, compile_one_page_resume, cover_letter_document
from job_agent.models import ApplicationRecord, Job
from job_agent.scoring import load_master_cv_text
from job_agent.scoring import score_job as score_job_core
from job_agent.snapshots import save_snapshot as save_snapshot_core
from job_agent.snapshots import verify_snapshot as verify_snapshot_core
from job_agent.strategy import (
    CareerStrategy,
    CareerStrategyStore,
    generate_career_strategy,
    strategy_context,
)
from job_agent.submission import Blocker, SubmissionRequest, platform_for_url
from job_agent.tailoring import generate_cover_letter as generate_cover_letter_core
from job_agent.tailoring import tailor_resume as tailor_resume_core
from job_agent.tracking import ApplicationTracker, CSVApplicationStore
from job_agent.xai_client import XAIClient, XAITextClient


def _airtable(settings: Settings) -> AirtableClient | None:
    if settings.airtable_pat is None or settings.airtable_base_id is None:
        return None
    return AirtableClient(
        settings.airtable_pat.get_secret_value(),
        settings.airtable_base_id,
    )


def _strategy_store(settings: Settings) -> CareerStrategyStore:
    return CareerStrategyStore(
        settings.career_strategy_path,
        settings.strategy_snapshot_dir,
    )


def create_server(settings: Settings | None = None, *, remote: bool = False) -> FastMCP:
    runtime = settings or Settings()
    auth = None
    if remote:
        if runtime.mcp_auth_token is None:
            raise RuntimeError("CAREERBOT_MCP_AUTH_TOKEN is required for remote MCP")
        token = runtime.mcp_auth_token.get_secret_value()
        auth = StaticTokenVerifier(
            tokens={
                token: {
                    "client_id": "careerbot-grok",
                    "scopes": ["careerbot:tools"],
                }
            },
            required_scopes=["careerbot:tools"],
        )

    mcp = FastMCP(
        "CareerBot",
        instructions=(
            "Bounded job scoring, tailoring, snapshot, and tracking tools. "
            "Never bypass a manual handoff or overwrite a snapshot."
        ),
        auth=auth,
        mask_error_details=remote,
    )

    @mcp.tool
    async def score_job(
        company: str,
        role: str,
        description: str,
        location: str | None = None,
        job_url: str | None = None,
        sponsorship: str | None = None,
    ) -> dict[str, Any]:
        """Score one job against the verified master resume."""
        if runtime.xai_api_key is None:
            raise ValueError("CAREERBOT_XAI_API_KEY is required")
        job = Job.model_validate(
            {
                "company": company,
                "role": role,
                "description": description,
                "location": location,
                "url": job_url,
                "sponsorship": sponsorship,
            }
        )
        async with XAIClient(
            runtime.xai_api_key.get_secret_value(),
            model=runtime.xai_model,
        ) as client:
            master_cv = load_master_cv_text(runtime.data_dir / "master_cv")
            approved_strategy = _strategy_store(runtime).load()
            result = await score_job_core(
                job,
                client,
                master_cv_text=master_cv,
                career_strategy_context=strategy_context(approved_strategy),
            )
        return result.model_dump(mode="json")

    @mcp.tool
    def consult_career_positioning(market_context: str = "") -> dict[str, Any]:
        """Generate a CV-grounded career strategy for review without saving it."""
        if runtime.xai_api_key is None:
            raise ValueError("CAREERBOT_XAI_API_KEY is required")
        master_cv = load_master_cv_text(runtime.data_dir / "master_cv")
        with XAITextClient(
            runtime.xai_api_key.get_secret_value(),
            model=runtime.xai_model,
        ) as client:
            strategy = generate_career_strategy(
                master_cv,
                client,
                market_context=market_context,
                model=runtime.xai_model,
            )
        return strategy.model_dump(mode="json")

    @mcp.tool
    def save_career_strategy(strategy: dict[str, Any]) -> dict[str, Any]:
        """Save an explicitly reviewed strategy and an immutable snapshot."""
        parsed = CareerStrategy.model_validate(strategy)
        snapshot = _strategy_store(runtime).save(parsed)
        return {
            "current_path": str(runtime.career_strategy_path),
            "snapshot_path": str(snapshot),
            "source_hash": parsed.source_hash,
        }

    @mcp.tool
    def get_career_strategy() -> dict[str, Any] | None:
        """Return the currently approved downstream career strategy."""
        strategy = _strategy_store(runtime).load()
        return strategy.model_dump(mode="json") if strategy is not None else None

    @mcp.tool
    def search_jobs(
        query: str,
        manual_jobs: list[dict[str, Any]] | None = None,
        email_alerts: list[dict[str, str]] | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """Normalize, rank, and deduplicate permitted supplied job data."""
        bounded_limit = min(limit or runtime.max_jobs_per_run, runtime.max_jobs_per_run)
        sources: list[JobSource] = []
        if manual_jobs:
            sources.append(ManualSource([Job.model_validate(item) for item in manual_jobs]))
        if email_alerts:
            sources.append(EmailAlertSource(email_alerts))
        approved_strategy = _strategy_store(runtime).load()
        target_terms = approved_strategy.target_terms() if approved_strategy else ()
        return [
            job.model_dump(mode="json")
            for job in discover_jobs(
                sources,
                query,
                limit=bounded_limit,
                **({"target_terms": target_terms} if target_terms else {}),
            )
        ]

    @mcp.tool
    def tailor_resume(job: dict[str, Any]) -> dict[str, Any]:
        """Tailor the master LaTeX resume and enforce all deterministic rules."""
        if runtime.xai_api_key is None:
            raise ValueError("CAREERBOT_XAI_API_KEY is required")
        if not runtime.master_resume_path.is_file():
            raise FileNotFoundError(
                "Install the verified master resume at data/master_resume.tex first"
            )
        master = runtime.master_resume_path.read_text(encoding="utf-8")
        with XAITextClient(
            runtime.xai_api_key.get_secret_value(),
            model=runtime.xai_model,
        ) as client:
            result = tailor_resume_core(Job.model_validate(job), master, client)
        return result.model_dump(mode="json")

    @mcp.tool
    def generate_cover_letter(
        job: dict[str, Any],
        tailored_resume_text: str,
    ) -> dict[str, Any]:
        """Generate a concise cover letter grounded in the tailored resume."""
        if runtime.xai_api_key is None:
            raise ValueError("CAREERBOT_XAI_API_KEY is required")
        with XAITextClient(
            runtime.xai_api_key.get_secret_value(),
            model=runtime.xai_model,
        ) as client:
            result = generate_cover_letter_core(
                Job.model_validate(job),
                tailored_resume_text,
                client,
            )
        return result.model_dump(mode="json")

    @mcp.tool
    def save_application_snapshot(
        job: dict[str, Any],
        resume_tex: str,
        cover_letter: str,
        changes: list[str],
        resume_version_note: str,
        score_report: dict[str, Any],
        source_hashes: dict[str, str],
        prompt_versions: dict[str, str],
        submitted_answers: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Compile and atomically save a complete immutable application package."""
        parsed = Job.model_validate(job)
        letter_tex = cover_letter_document(cover_letter)
        with tempfile.TemporaryDirectory(prefix="careerbot-package-") as temporary:
            output = Path(temporary)
            resume_build = compile_one_page_resume(resume_tex, output, stem="resume")
            letter_build = compile_latex(
                letter_tex,
                output,
                stem="cover_letter",
                require_one_page=True,
            )
            path = save_snapshot_core(
                runtime.snapshot_dir,
                company=parsed.company,
                role=parsed.role,
                resume_tex=resume_tex,
                cover_letter=cover_letter,
                snapshot_note=resume_version_note,
                source_hashes=source_hashes,
                prompt_versions=prompt_versions,
                model=runtime.xai_model,
                source_url=str(parsed.url) if parsed.url else None,
                resume_pdf=resume_build.pdf_path,
                cover_letter_tex=letter_tex,
                cover_letter_pdf=letter_build.pdf_path,
                job_description=parsed.description,
                score_report=score_report,
                changes=changes,
                submitted_answers=submitted_answers,
            )
        return {
            "snapshot_path": str(path),
            "manifest": verify_snapshot_core(path).model_dump(mode="json"),
        }

    @mcp.tool
    def track_application(record: dict[str, Any]) -> dict[str, Any]:
        """Upsert an application in Airtable when configured and in the CSV backup."""
        parsed = ApplicationRecord.model_validate(record)
        airtable = _airtable(runtime)
        try:
            tracker = ApplicationTracker(
                CSVApplicationStore(runtime.application_log_path),
                airtable=airtable,
            )
            return tracker.track(parsed).model_dump(mode="json")
        finally:
            if airtable is not None:
                airtable.close()

    @mcp.tool
    def verify_snapshot(snapshot_path: str) -> dict[str, Any]:
        """Verify immutable artifact sizes and SHA-256 hashes."""
        root = Path(snapshot_path).resolve()
        allowed = runtime.snapshot_dir.resolve()
        root.relative_to(allowed)
        return verify_snapshot_core(root).model_dump(mode="json")

    @mcp.tool
    def submission_hard_stops() -> list[str]:
        """Return conditions that always require a manual handoff."""
        return [blocker.value for blocker in Blocker]

    @mcp.tool
    def assess_submission(
        source_url: str,
        captcha_present: bool = False,
        mfa_required: bool = False,
        identity_verification_required: bool = False,
        consent_or_declaration_required: bool = False,
        ambiguous_questions: list[str] | None = None,
    ) -> dict[str, Any]:
        """Decide whether an application can use an authorized automatic connector."""
        platform, automation_permitted = platform_for_url(source_url)
        request = SubmissionRequest(
            source_url=source_url,
            captcha_present=captcha_present,
            mfa_required=mfa_required,
            identity_verification_required=identity_verification_required,
            consent_or_declaration_required=consent_or_declaration_required,
            ambiguous_questions=tuple(ambiguous_questions or ()),
        )
        blockers: list[str] = []
        if not automation_permitted:
            blockers.append(Blocker.RESTRICTED_PLATFORM.value)
        if request.captcha_present:
            blockers.append(Blocker.CAPTCHA.value)
        if request.mfa_required:
            blockers.append(Blocker.MFA.value)
        if request.identity_verification_required:
            blockers.append(Blocker.IDENTITY_VERIFICATION.value)
        if request.consent_or_declaration_required:
            blockers.append(Blocker.CONSENT.value)
        if request.ambiguous_questions:
            blockers.append(Blocker.AMBIGUOUS_ANSWER.value)
        return {
            "platform": platform,
            "automation_permitted": automation_permitted and not blockers,
            "blockers": blockers,
            "action": "manual_handoff" if blockers else "authorized_connector_required",
        }

    return mcp


def main() -> None:
    transport = os.getenv("CAREERBOT_MCP_TRANSPORT", "stdio").casefold()
    if transport == "stdio":
        create_server().run(transport="stdio")
        return
    if transport not in {"http", "streamable-http", "sse"}:
        raise ValueError(f"unsupported MCP transport: {transport}")
    host = os.getenv("CAREERBOT_MCP_HOST", "127.0.0.1")
    port = int(os.getenv("CAREERBOT_MCP_PORT", "8000"))
    server = create_server(remote=True)
    if transport == "sse":
        server.run(transport="sse", host=host, port=port)
    elif transport == "http":
        server.run(transport="http", host=host, port=port)
    else:
        server.run(transport="streamable-http", host=host, port=port)


if __name__ == "__main__":
    main()
