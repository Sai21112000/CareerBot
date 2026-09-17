"""Small, testable Airtable REST client.

The client deliberately accepts an ``httpx`` transport so tests and callers can use
``MockTransport`` without credentials or network access.
"""

from __future__ import annotations

import random
import time
from collections.abc import Callable, Iterator, Mapping, Sequence
from typing import Any, cast
from urllib.parse import quote

import httpx


class AirtableError(RuntimeError):
    """Raised when Airtable cannot complete a request."""


class AirtableClient:
    def __init__(
        self,
        token: str,
        base_id: str,
        *,
        transport: httpx.BaseTransport | None = None,
        client: httpx.Client | None = None,
        timeout: float = 20.0,
        max_retries: int = 3,
        backoff_base: float = 0.25,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if not token or not base_id:
            raise ValueError("token and base_id are required")
        if client is not None and transport is not None:
            raise ValueError("pass client or transport, not both")
        self.base_id = base_id
        self.max_retries = max_retries
        self.backoff_base = backoff_base
        self._sleep = sleep
        self._owns_client = client is None
        self._client = client or httpx.Client(
            base_url="https://api.airtable.com/v0/",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            timeout=timeout,
            transport=transport,
        )

    def __enter__(self) -> AirtableClient:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        retryable = {408, 409, 429, 500, 502, 503, 504}
        for attempt in range(self.max_retries + 1):
            try:
                response = self._client.request(method, path, **kwargs)
                if response.status_code not in retryable:
                    response.raise_for_status()
                    payload = response.json()
                    if not isinstance(payload, dict):
                        raise AirtableError("Airtable returned a non-object response")
                    return payload
                if attempt == self.max_retries:
                    response.raise_for_status()
                retry_after = response.headers.get("Retry-After")
            except (httpx.TransportError, httpx.TimeoutException) as exc:
                if attempt == self.max_retries:
                    raise AirtableError(f"Airtable request failed: {exc}") from exc
                retry_after = None
            except httpx.HTTPStatusError as exc:
                message = exc.response.text[:500]
                raise AirtableError(
                    f"Airtable returned HTTP {exc.response.status_code}: {message}"
                ) from exc

            if retry_after is not None:
                try:
                    delay = float(retry_after)
                except ValueError:
                    delay = self.backoff_base * (2**attempt)
            else:
                delay = self.backoff_base * (2**attempt) * (0.75 + random.random() * 0.5)
            self._sleep(delay)
        raise AssertionError("unreachable")

    def _table_path(self, table: str) -> str:
        return f"{quote(self.base_id, safe='')}/{quote(table, safe='')}"

    def iter_records(
        self,
        table: str,
        *,
        formula: str | None = None,
        fields: Sequence[str] | None = None,
        page_size: int = 100,
        max_records: int | None = None,
    ) -> Iterator[dict[str, Any]]:
        params: list[tuple[str, str | int]] = [("pageSize", min(page_size, 100))]
        if formula:
            params.append(("filterByFormula", formula))
        params.extend(("fields[]", field) for field in fields or ())
        yielded = 0
        while True:
            payload = self._request("GET", self._table_path(table), params=params)
            for record in payload.get("records", []):
                if not isinstance(record, dict):
                    continue
                yield record
                yielded += 1
                if max_records is not None and yielded >= max_records:
                    return
            offset = payload.get("offset")
            if not offset:
                return
            params = [(key, value) for key, value in params if key != "offset"]
            params.append(("offset", str(offset)))

    def create_record(
        self, table: str, fields: Mapping[str, Any], *, typecast: bool = False
    ) -> dict[str, Any]:
        return self._request(
            "POST",
            self._table_path(table),
            json={"fields": dict(fields), "typecast": typecast},
        )

    def update_record(
        self, table: str, record_id: str, fields: Mapping[str, Any]
    ) -> dict[str, Any]:
        return self._request(
            "PATCH",
            f"{self._table_path(table)}/{quote(record_id, safe='')}",
            json={"fields": dict(fields)},
        )

    def upsert_records(
        self,
        table: str,
        records: Sequence[Mapping[str, Any]],
        *,
        merge_fields: Sequence[str],
        typecast: bool = False,
    ) -> dict[str, Any]:
        """Atomically upsert records using Airtable's performUpsert operation.

        ``merge_fields`` must identify a deterministic key such as ``idempotency_key``.
        Airtable accepts at most ten records per request, so larger inputs are chunked.
        """
        if not merge_fields:
            raise ValueError("merge_fields must not be empty")
        all_records: list[dict[str, Any]] = []
        created: list[str] = []
        updated: list[str] = []
        for start in range(0, len(records), 10):
            chunk = records[start : start + 10]
            payload = self._request(
                "PATCH",
                self._table_path(table),
                json={
                    "performUpsert": {"fieldsToMergeOn": list(merge_fields)},
                    "records": [{"fields": dict(record)} for record in chunk],
                    "typecast": typecast,
                },
            )
            all_records.extend(payload.get("records", []))
            created.extend(payload.get("createdRecords", []))
            updated.extend(payload.get("updatedRecords", []))
        return {"records": all_records, "createdRecords": created, "updatedRecords": updated}

    def upsert_record(
        self, table: str, fields: Mapping[str, Any], *, merge_fields: Sequence[str]
    ) -> dict[str, Any]:
        response = self.upsert_records(table, [fields], merge_fields=merge_fields)
        records = response["records"]
        if not records:
            raise AirtableError("Airtable upsert returned no record")
        return cast(dict[str, Any], records[0])
