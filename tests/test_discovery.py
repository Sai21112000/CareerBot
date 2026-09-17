import pytest

from job_agent.discovery import (
    EmailAlertSource,
    ManualSource,
    RestrictedSourceError,
    deduplicate_jobs,
    discover_jobs,
)
from job_agent.models import Job


def job(**changes: object) -> Job:
    values = {
        "company": "Geo AI",
        "role": "Computer Vision Engineer",
        "description": "Remote sensing and machine learning",
        "url": "https://example.com/jobs/1?utm_source=alert",
        "location": "Bangkok, Thailand",
    }
    values.update(changes)
    return Job.model_validate(values)


def test_manual_and_email_discovery_deduplicate_and_rank() -> None:
    manual = ManualSource([job()])
    email = EmailAlertSource(
        [
            {
                "company": "Geo AI",
                "role": "Computer Vision Engineer",
                "description": "Remote sensing and machine learning with more detail",
                "url": "https://example.com/jobs/1",
                "location": "Bangkok, Thailand",
            },
            {
                "company": "Other",
                "role": "Accountant",
                "description": "Accounting",
            },
        ]
    )
    results = discover_jobs([manual, email], "engineer", limit=5)
    assert len(results) == 1
    assert results[0].fingerprint


def test_restricted_source_stops_before_search() -> None:
    source = ManualSource([job()])
    source.automation_permitted = False
    with pytest.raises(RestrictedSourceError):
        discover_jobs([source], "", limit=1)


def test_external_ids_are_source_scoped() -> None:
    jobs = [
        job(external_id="1", source="one"),
        job(external_id="1", source="two"),
    ]
    assert len(deduplicate_jobs(jobs)) == 2
