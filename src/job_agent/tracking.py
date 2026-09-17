"""Durable application tracking with CSV fallback and reconciliation."""

from __future__ import annotations

import csv
import json
import os
import tempfile
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

from job_agent.airtable import AirtableClient
from job_agent.models import ApplicationRecord

APPLICATION_LOG_COLUMNS = (
    "idempotency_key",
    "date_applied",
    "company",
    "role",
    "job_url",
    "snapshot_path",
    "resume_version_note",
    "status",
    "applied_via",
    "follow_up_date",
    "confirmation_id",
    "submitted_answers",
    "updated_at",
)
REQUIRED_APPLICATION_COLUMNS = APPLICATION_LOG_COLUMNS


def _serialize(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return str(value.value if hasattr(value, "value") else value)


def record_to_row(record: ApplicationRecord) -> dict[str, str]:
    dumped = record.model_dump()
    return {column: _serialize(dumped[column]) for column in APPLICATION_LOG_COLUMNS}


def row_to_record(row: Mapping[str, str]) -> ApplicationRecord:
    missing = set(APPLICATION_LOG_COLUMNS) - row.keys()
    if missing:
        raise ValueError(f"application row missing columns: {sorted(missing)}")
    payload: dict[str, Any] = dict(row)
    for optional in (
        "date_applied",
        "job_url",
        "applied_via",
        "follow_up_date",
        "confirmation_id",
    ):
        payload[optional] = payload[optional] or None
    payload["submitted_answers"] = json.loads(payload["submitted_answers"] or "{}")
    return ApplicationRecord.model_validate(payload)


class CSVApplicationStore:
    """Atomic, idempotent CSV storage suitable as a local backup."""

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)

    def read_all(self) -> list[ApplicationRecord]:
        if not self.path.exists():
            return []
        with self.path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            if tuple(reader.fieldnames or ()) != APPLICATION_LOG_COLUMNS:
                raise ValueError(
                    f"CSV columns must exactly equal {list(APPLICATION_LOG_COLUMNS)}"
                )
            return [row_to_record(row) for row in reader]

    def upsert(self, record: ApplicationRecord) -> ApplicationRecord:
        records = {item.idempotency_key: item for item in self.read_all()}
        current = records.get(record.idempotency_key)
        if current is None or record.updated_at >= current.updated_at:
            records[record.idempotency_key] = record
        self.write_all(records.values())
        return records[record.idempotency_key]

    def write_all(self, records: Iterable[ApplicationRecord]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, name = tempfile.mkstemp(
            dir=self.path.parent, prefix=f".{self.path.name}.", suffix=".tmp", text=True
        )
        try:
            with os.fdopen(fd, "w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=APPLICATION_LOG_COLUMNS)
                writer.writeheader()
                for record in sorted(records, key=lambda item: item.idempotency_key):
                    writer.writerow(record_to_row(record))
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(name, self.path)
        except BaseException:
            Path(name).unlink(missing_ok=True)
            raise


def record_to_airtable_fields(record: ApplicationRecord) -> dict[str, Any]:
    """Map the canonical record to stable Airtable field names."""
    return record_to_row(record)


@dataclass(frozen=True)
class Reconciliation:
    csv_only: tuple[str, ...]
    remote_only: tuple[str, ...]
    differing: tuple[str, ...]
    matching: tuple[str, ...]


def reconcile_records(
    local: Iterable[ApplicationRecord], remote: Iterable[ApplicationRecord]
) -> Reconciliation:
    local_by_key = {record.idempotency_key: record for record in local}
    remote_by_key = {record.idempotency_key: record for record in remote}
    local_keys, remote_keys = set(local_by_key), set(remote_by_key)
    common = local_keys & remote_keys
    differing = {
        key
        for key in common
        if record_to_row(local_by_key[key]) != record_to_row(remote_by_key[key])
    }
    return Reconciliation(
        csv_only=tuple(sorted(local_keys - remote_keys)),
        remote_only=tuple(sorted(remote_keys - local_keys)),
        differing=tuple(sorted(differing)),
        matching=tuple(sorted(common - differing)),
    )


class ApplicationTracker:
    """Airtable-first tracker with an atomic local CSV export/backup."""

    def __init__(
        self,
        csv_store: CSVApplicationStore,
        *,
        airtable: AirtableClient | None = None,
        table: str = "Applications",
    ) -> None:
        self.csv_store = csv_store
        self.airtable = airtable
        self.table = table

    def track(self, record: ApplicationRecord) -> ApplicationRecord:
        if self.airtable is not None:
            self.airtable.upsert_record(
                self.table,
                record_to_airtable_fields(record),
                merge_fields=("idempotency_key",),
            )
        return self.csv_store.upsert(record)
