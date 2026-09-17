from pathlib import Path

import httpx

from job_agent.airtable import AirtableClient
from job_agent.models import ApplicationRecord
from job_agent.tracking import (
    APPLICATION_LOG_COLUMNS,
    CSVApplicationStore,
    reconcile_records,
)


def application(key: str = "key-1", company: str = "Acme") -> ApplicationRecord:
    return ApplicationRecord(
        idempotency_key=key,
        company=company,
        role="Computer Vision Engineer",
        snapshot_path=Path("snapshots/acme"),
        resume_version_note="tailored-v1",
    )


def test_csv_has_exact_columns_and_upserts(tmp_path: Path) -> None:
    store = CSVApplicationStore(tmp_path / "applications.csv")
    store.upsert(application())
    store.upsert(application(company="Acme AI"))

    assert store.path.read_text().splitlines()[0].split(",") == list(
        APPLICATION_LOG_COLUMNS
    )
    records = store.read_all()
    assert len(records) == 1
    assert records[0].company == "Acme AI"


def test_reconciliation_reports_each_class() -> None:
    same = application("same")
    result = reconcile_records(
        [same, application("local")],
        [same, application("remote")],
    )
    assert result.matching == ("same",)
    assert result.csv_only == ("local",)
    assert result.remote_only == ("remote",)


def test_airtable_retries_and_uses_native_upsert() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if len(requests) == 1:
            return httpx.Response(429, headers={"Retry-After": "0"})
        return httpx.Response(
            200,
            json={"records": [{"id": "rec1", "fields": {"idempotency_key": "key-1"}}]},
        )

    client = AirtableClient(
        "token",
        "base",
        transport=httpx.MockTransport(handler),
        sleep=lambda _: None,
    )
    result = client.upsert_record(
        "Applications",
        {"idempotency_key": "key-1"},
        merge_fields=("idempotency_key",),
    )
    client.close()

    assert result["id"] == "rec1"
    assert len(requests) == 2
    assert b"performUpsert" in requests[-1].content
