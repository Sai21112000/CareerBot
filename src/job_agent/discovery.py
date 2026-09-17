"""Policy-aware job discovery, normalization, deduplication, and ranking."""

from __future__ import annotations

import hashlib
import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from job_agent.models import Job


class RestrictedSourceError(RuntimeError):
    """Raised before accessing a source that does not permit automation."""


class JobSource(Protocol):
    name: str
    automation_permitted: bool

    def search(self, query: str, *, limit: int) -> Iterable[Job]: ...


@dataclass
class ManualSource:
    jobs: Sequence[Job]
    name: str = "manual"
    automation_permitted: bool = True

    def search(self, query: str, *, limit: int) -> Iterable[Job]:
        terms = query.casefold().split()
        for job in self.jobs:
            haystack = f"{job.role} {job.company} {job.description}".casefold()
            if not terms or any(term in haystack for term in terms):
                yield job.model_copy(update={"source": self.name})
                limit -= 1
                if limit <= 0:
                    return


@dataclass
class EmailAlertSource:
    """Turns already-authorized, parsed email alert data into jobs."""

    alerts: Sequence[Mapping[str, str]]
    name: str = "email_alert"
    automation_permitted: bool = True

    def search(self, query: str, *, limit: int) -> Iterable[Job]:
        terms = query.casefold().split()
        for alert in self.alerts:
            role = alert.get("role") or alert.get("title") or ""
            company = alert.get("company", "")
            description = alert.get("description") or role
            haystack = f"{role} {company} {description}".casefold()
            if terms and not any(term in haystack for term in terms):
                continue
            yield Job.model_validate(
                {
                    "external_id": alert.get("external_id"),
                    "company": company,
                    "role": role,
                    "description": description,
                    "url": alert.get("url") or None,
                    "location": alert.get("location") or None,
                    "source": self.name,
                    "sponsorship": alert.get("sponsorship") or None,
                }
            )
            limit -= 1
            if limit <= 0:
                return


@dataclass
class PermittedSourceAdapter:
    """Adapter for a caller-supplied search function with explicit permission."""

    name: str
    fetch: object
    automation_permitted: bool = True

    def search(self, query: str, *, limit: int) -> Iterable[Job]:
        if not self.automation_permitted:
            raise RestrictedSourceError(f"automation is not permitted for source {self.name}")
        result = self.fetch(query, limit=limit)  # type: ignore[operator]
        return (
            item.model_copy(update={"source": self.name})
            for item in result
            if isinstance(item, Job)
        )


def canonicalize_url(url: object | None) -> str:
    if not url:
        return ""
    parts = urlsplit(str(url))
    tracking = {
        "fbclid",
        "gclid",
        "ref",
        "source",
        "trk",
        "utm_campaign",
        "utm_medium",
        "utm_source",
    }
    query = urlencode(
        sorted(
            (key, value)
            for key, value in parse_qsl(parts.query)
            if key.casefold() not in tracking
        )
    )
    return urlunsplit(
        (parts.scheme.casefold(), parts.netloc.casefold(), parts.path.rstrip("/"), query, "")
    )


def job_fingerprint(job: Job) -> str:
    if job.external_id:
        basis = f"{job.source.casefold()}:{job.external_id.casefold()}"
    else:
        def normalized(value: str) -> str:
            return re.sub(r"\W+", " ", value.casefold()).strip()

        basis = "|".join(
            (normalized(job.company), normalized(job.role), canonicalize_url(job.url))
        )
    return hashlib.sha256(basis.encode()).hexdigest()


def deduplicate_jobs(jobs: Iterable[Job]) -> list[Job]:
    unique: dict[str, Job] = {}
    for job in jobs:
        fingerprint = job.fingerprint or job_fingerprint(job)
        candidate = job.model_copy(update={"fingerprint": fingerprint})
        current = unique.get(fingerprint)
        if current is None or len(candidate.description) > len(current.description):
            unique[fingerprint] = candidate
    return list(unique.values())


DEFAULT_TARGET_TERMS = (
    "computer vision",
    "geospatial",
    "remote sensing",
    "machine learning",
    "applied ai",
    "llm",
    "agent",
    "forward deployed",
)


def rank_job(job: Job, *, target_terms: Sequence[str] = DEFAULT_TARGET_TERMS) -> int:
    text = f"{job.role} {job.description}".casefold()
    score = sum(8 for term in target_terms if term.casefold() in text)
    role = job.role.casefold()
    score += sum(12 for term in target_terms if term.casefold() in role)
    location = (job.location or "").casefold()
    if "thailand" in location or "bangkok" in location:
        score += 20
    sponsorship = (job.sponsorship or "").casefold()
    if any(term in sponsorship for term in ("yes", "sponsor", "visa support")):
        score += 15
    if any(term in sponsorship for term in ("no sponsorship", "not sponsor")):
        score -= 20
    return score


def discover_jobs(
    sources: Iterable[JobSource],
    query: str,
    *,
    limit: int,
    target_terms: Sequence[str] = DEFAULT_TARGET_TERMS,
) -> list[Job]:
    if limit < 1:
        return []
    found: list[Job] = []
    for source in sources:
        if not source.automation_permitted:
            raise RestrictedSourceError(f"automation is not permitted for source {source.name}")
        remaining = limit - len(found)
        if remaining <= 0:
            break
        found.extend(source.search(query, limit=remaining))
    unique = deduplicate_jobs(found)
    unique.sort(key=lambda job: (-rank_job(job, target_terms=target_terms), job.company.casefold()))
    return unique[:limit]
