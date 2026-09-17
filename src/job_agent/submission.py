"""Submission policy, connector capabilities, and idempotent state transitions."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Protocol, runtime_checkable
from urllib.parse import urlsplit

from job_agent.models import ApplicationRecord, ApplicationStatus, Handoff, utc_now


class Blocker(StrEnum):
    RESTRICTED_PLATFORM = "restricted_platform"
    CAPTCHA = "captcha"
    MFA = "mfa"
    IDENTITY_VERIFICATION = "identity_verification"
    CONSENT = "consent_or_declaration"
    AMBIGUOUS_ANSWER = "ambiguous_answer"
    UNSUPPORTED_CONNECTOR = "unsupported_connector"


@dataclass(frozen=True)
class ConnectorCapabilities:
    platform: str
    automation_permitted: bool
    supports_submission: bool = True
    supports_file_upload: bool = True
    supports_custom_answers: bool = True


@dataclass(frozen=True)
class SubmissionRequest:
    source_url: str
    answers: Mapping[str, Any] = field(default_factory=dict)
    files: Mapping[str, str] = field(default_factory=dict)
    captcha_present: bool = False
    mfa_required: bool = False
    identity_verification_required: bool = False
    consent_or_declaration_required: bool = False
    user_confirmed_consent: bool = False
    ambiguous_questions: tuple[str, ...] = ()


@dataclass(frozen=True)
class ConnectorResult:
    confirmation_id: str
    evidence: Mapping[str, Any] = field(default_factory=dict)


@runtime_checkable
class SubmissionConnector(Protocol):
    @property
    def capabilities(self) -> ConnectorCapabilities: ...

    def submit(self, request: SubmissionRequest) -> ConnectorResult: ...


@dataclass(frozen=True)
class SubmissionOutcome:
    record: ApplicationRecord
    handoff: Handoff | None = None
    evidence: Mapping[str, Any] = field(default_factory=dict)


ALLOWED_TRANSITIONS: dict[ApplicationStatus, frozenset[ApplicationStatus]] = {
    ApplicationStatus.PREPARED: frozenset(
        {ApplicationStatus.READY, ApplicationStatus.HANDOFF, ApplicationStatus.FAILED}
    ),
    ApplicationStatus.READY: frozenset(
        {ApplicationStatus.SUBMITTING, ApplicationStatus.HANDOFF, ApplicationStatus.FAILED}
    ),
    ApplicationStatus.SUBMITTING: frozenset(
        {ApplicationStatus.SUBMITTED, ApplicationStatus.HANDOFF, ApplicationStatus.FAILED}
    ),
    ApplicationStatus.SUBMITTED: frozenset(),
    ApplicationStatus.HANDOFF: frozenset({ApplicationStatus.READY}),
    ApplicationStatus.FAILED: frozenset({ApplicationStatus.READY}),
}


def transition(record: ApplicationRecord, status: ApplicationStatus) -> ApplicationRecord:
    if status == record.status:
        return record
    if status not in ALLOWED_TRANSITIONS[record.status]:
        raise ValueError(f"invalid application transition: {record.status} -> {status}")
    return record.model_copy(update={"status": status, "updated_at": utc_now()})


def submission_blocker(
    connector: SubmissionConnector, request: SubmissionRequest
) -> tuple[Blocker, str, list[str]] | None:
    capabilities = connector.capabilities
    if not capabilities.automation_permitted:
        return (
            Blocker.RESTRICTED_PLATFORM,
            f"automation is not permitted for {capabilities.platform}",
            ["Open the source URL and complete the application manually."],
        )
    if not capabilities.supports_submission:
        return (
            Blocker.UNSUPPORTED_CONNECTOR,
            f"{capabilities.platform} connector cannot submit applications",
            ["Complete submission manually."],
        )
    if request.captcha_present:
        return (Blocker.CAPTCHA, "CAPTCHA requires a person", ["Complete the CAPTCHA manually."])
    if request.mfa_required:
        return (Blocker.MFA, "MFA requires the account owner", ["Complete MFA manually."])
    if request.identity_verification_required:
        return (
            Blocker.IDENTITY_VERIFICATION,
            "identity verification requires the applicant",
            ["Complete identity verification manually."],
        )
    if request.consent_or_declaration_required and not request.user_confirmed_consent:
        return (
            Blocker.CONSENT,
            "consent or declaration requires explicit user confirmation",
            ["Review and personally confirm the consent or declaration."],
        )
    if request.ambiguous_questions:
        questions = ", ".join(request.ambiguous_questions)
        return (
            Blocker.AMBIGUOUS_ANSWER,
            f"answers require user clarification: {questions}",
            ["Provide explicit answers before resuming."],
        )
    if request.files and not capabilities.supports_file_upload:
        return (
            Blocker.UNSUPPORTED_CONNECTOR,
            "connector cannot upload required files",
            ["Upload the required files manually."],
        )
    if request.answers and not capabilities.supports_custom_answers:
        return (
            Blocker.UNSUPPORTED_CONNECTOR,
            "connector cannot answer custom questions",
            ["Answer the custom questions manually."],
        )
    return None


def _handoff(
    record: ApplicationRecord,
    request: SubmissionRequest,
    reason: str,
    actions: list[str],
) -> SubmissionOutcome:
    if (
        record.status not in {ApplicationStatus.HANDOFF, ApplicationStatus.SUBMITTED}
        and ApplicationStatus.HANDOFF in ALLOWED_TRANSITIONS[record.status]
    ):
        record = transition(record, ApplicationStatus.HANDOFF)
    return SubmissionOutcome(
        record=record,
        handoff=Handoff(reason=reason, url=request.source_url, required_actions=actions),
    )


class SubmissionService:
    """Applies hard-stop policy before a connector is allowed to submit."""

    def submit(
        self,
        record: ApplicationRecord,
        request: SubmissionRequest,
        connector: SubmissionConnector,
    ) -> SubmissionOutcome:
        if record.status == ApplicationStatus.SUBMITTED:
            return SubmissionOutcome(record=record)

        blocked = submission_blocker(connector, request)
        if blocked:
            _, reason, actions = blocked
            return _handoff(record, request, reason, actions)

        if record.status in {
            ApplicationStatus.HANDOFF,
            ApplicationStatus.FAILED,
            ApplicationStatus.PREPARED,
        }:
            record = transition(record, ApplicationStatus.READY)
        if record.status == ApplicationStatus.READY:
            record = transition(record, ApplicationStatus.SUBMITTING)

        try:
            result = connector.submit(request)
        except Exception as exc:
            failed = transition(record, ApplicationStatus.FAILED)
            return SubmissionOutcome(
                record=failed,
                evidence={"error": f"{type(exc).__name__}: {exc}"},
            )
        record = transition(record, ApplicationStatus.SUBMITTED).model_copy(
            update={
                "confirmation_id": result.confirmation_id,
                "submitted_answers": dict(request.answers),
                "job_url": record.job_url or request.source_url,
            }
        )
        return SubmissionOutcome(record=record, evidence=result.evidence)


RESTRICTED_HOSTS = frozenset(
    {
        "linkedin.com",
        "www.linkedin.com",
        "jobsdb.com",
        "th.jobsdb.com",
        "jobthai.com",
        "www.jobthai.com",
        "workventure.com",
        "www.workventure.com",
        "jobtopgun.com",
        "www.jobtopgun.com",
        "jobbkk.com",
        "www.jobbkk.com",
    }
)


def platform_for_url(url: str) -> tuple[str, bool]:
    """Return a normalized platform and whether unattended automation is permitted."""
    host = (urlsplit(url).hostname or "").casefold()
    restricted = host in RESTRICTED_HOSTS or any(
        host.endswith(f".{candidate}") for candidate in RESTRICTED_HOSTS
    )
    return (host or "unknown", not restricted)


@dataclass
class AuthorizedAPIConnector:
    """Adapter for a user-authorized API submission function."""

    capabilities: ConnectorCapabilities
    submit_call: Any

    def submit(self, request: SubmissionRequest) -> ConnectorResult:
        if not callable(self.submit_call):
            raise TypeError("submit_call must be callable")
        result = self.submit_call(request)
        if isinstance(result, ConnectorResult):
            return result
        if not isinstance(result, Mapping):
            raise TypeError("authorized connector must return a mapping or ConnectorResult")
        return ConnectorResult(
            confirmation_id=str(result["confirmation_id"]),
            evidence=dict(result.get("evidence", {})),
        )


@dataclass
class ConnectorQualification:
    """Supervised evidence required before a connector may run in auto mode."""

    connector: str
    replay_tests_passed: bool = False
    supervised_successes: int = 0
    duplicate_prevention_verified: bool = False
    field_mapping_verified: bool = False
    minimum_supervised_successes: int = 2

    @property
    def auto_eligible(self) -> bool:
        return (
            self.replay_tests_passed
            and self.duplicate_prevention_verified
            and self.field_mapping_verified
            and self.supervised_successes >= self.minimum_supervised_successes
        )
