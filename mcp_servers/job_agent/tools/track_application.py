"""MCP-callable application tracking operation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from job_agent.airtable import AirtableClient
from job_agent.models import ApplicationRecord
from job_agent.tracking import ApplicationTracker, CSVApplicationStore


def track_application(
    record: ApplicationRecord | dict[str, Any],
    *,
    csv_path: str | Path = "data/applications_log.csv",
    airtable: AirtableClient | None = None,
    table: str = "Applications",
) -> dict[str, Any]:
    """Idempotently track an application locally and optionally in Airtable.

    Credentials are intentionally not loaded here. The composition root may inject an
    authenticated client, while offline and dry-run use remains local-only.
    """
    validated = (
        record
        if isinstance(record, ApplicationRecord)
        else ApplicationRecord.model_validate(record)
    )
    tracker = ApplicationTracker(
        CSVApplicationStore(csv_path),
        airtable=airtable,
        table=table,
    )
    return tracker.track(validated).model_dump(mode="json")
