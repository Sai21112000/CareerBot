from pathlib import Path

import pytest

from job_agent.models import ApplicationRecord, ApplicationStatus
from job_agent.submission import (
    AuthorizedAPIConnector,
    ConnectorCapabilities,
    ConnectorQualification,
    ConnectorResult,
    SubmissionRequest,
    SubmissionService,
    platform_for_url,
    transition,
)


class Connector:
    def __init__(self, permitted: bool = True) -> None:
        self.capabilities = ConnectorCapabilities(
            platform="example", automation_permitted=permitted
        )
        self.calls = 0

    def submit(self, request: SubmissionRequest) -> ConnectorResult:
        self.calls += 1
        return ConnectorResult("confirmation-1", {"url": request.source_url})


def record(status: ApplicationStatus = ApplicationStatus.PREPARED) -> ApplicationRecord:
    return ApplicationRecord(
        idempotency_key="key",
        company="Acme",
        role="ML Engineer",
        snapshot_path=Path("snapshot"),
        resume_version_note="v1",
        status=status,
    )


@pytest.mark.parametrize(
    "submission_request",
    [
        SubmissionRequest("https://example.com", captcha_present=True),
        SubmissionRequest("https://example.com", mfa_required=True),
        SubmissionRequest("https://example.com", identity_verification_required=True),
        SubmissionRequest("https://example.com", consent_or_declaration_required=True),
        SubmissionRequest("https://example.com", ambiguous_questions=("salary",)),
    ],
)
def test_hard_stops_return_handoff_without_connector_call(
    submission_request: SubmissionRequest,
) -> None:
    connector = Connector()
    outcome = SubmissionService().submit(record(), submission_request, connector)
    assert outcome.record.status == ApplicationStatus.HANDOFF
    assert outcome.handoff is not None
    assert connector.calls == 0


def test_restricted_platform_hard_stops() -> None:
    connector = Connector(permitted=False)
    outcome = SubmissionService().submit(
        record(), SubmissionRequest("https://example.com"), connector
    )
    assert outcome.record.status == ApplicationStatus.HANDOFF
    assert connector.calls == 0


def test_submission_is_idempotent_after_confirmation() -> None:
    connector = Connector()
    service = SubmissionService()
    first = service.submit(record(), SubmissionRequest("https://example.com"), connector)
    second = service.submit(
        first.record, SubmissionRequest("https://example.com"), connector
    )
    assert second.record.status == ApplicationStatus.SUBMITTED
    assert connector.calls == 1


def test_invalid_transition_is_rejected() -> None:
    with pytest.raises(ValueError):
        transition(record(), ApplicationStatus.SUBMITTED)


def test_restricted_job_sites_are_detected_before_adapter_use() -> None:
    assert platform_for_url("https://www.linkedin.com/jobs/view/1") == (
        "www.linkedin.com",
        False,
    )
    assert platform_for_url("https://careers.example.com/jobs/1") == (
        "careers.example.com",
        True,
    )


def test_authorized_api_adapter_and_auto_qualification() -> None:
    connector = AuthorizedAPIConnector(
        ConnectorCapabilities(platform="approved-ats", automation_permitted=True),
        lambda request: {
            "confirmation_id": "confirmed-2",
            "evidence": {"url": request.source_url},
        },
    )
    outcome = SubmissionService().submit(
        record(),
        SubmissionRequest("https://careers.example.com/jobs/1"),
        connector,
    )
    assert outcome.record.status is ApplicationStatus.SUBMITTED

    qualification = ConnectorQualification(
        "approved-ats",
        replay_tests_passed=True,
        supervised_successes=2,
        duplicate_prevention_verified=True,
        field_mapping_verified=True,
    )
    assert qualification.auto_eligible
