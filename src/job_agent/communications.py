"""Credential-neutral protocols for email and calendar integrations."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class EmailMessage:
    recipient: str
    subject: str
    body: str
    thread_id: str | None = None


@dataclass(frozen=True)
class EmailReceipt:
    message_id: str
    thread_id: str | None = None


@dataclass(frozen=True)
class CalendarEvent:
    title: str
    starts_at: datetime
    ends_at: datetime
    description: str = ""
    attendees: tuple[str, ...] = ()
    idempotency_key: str | None = None


@dataclass(frozen=True)
class CalendarReceipt:
    event_id: str
    html_link: str | None = None


@runtime_checkable
class MailClient(Protocol):
    def send(self, message: EmailMessage) -> EmailReceipt: ...

    def search(self, query: str, *, limit: int = 20) -> Sequence[Mapping[str, str]]: ...


@runtime_checkable
class CalendarClient(Protocol):
    def create_event(self, event: CalendarEvent) -> CalendarReceipt: ...

    def find_event(self, idempotency_key: str) -> CalendarReceipt | None: ...


# Descriptive aliases for callers that use provider-specific terminology. Implementations
# can wrap Gmail or Google Calendar without those optional SDKs entering the core package.
GmailClient = MailClient
GoogleCalendarClient = CalendarClient


class InMemoryMailClient:
    """Offline implementation useful for dry runs and tests."""

    def __init__(self) -> None:
        self.sent: list[EmailMessage] = []

    def send(self, message: EmailMessage) -> EmailReceipt:
        self.sent.append(message)
        return EmailReceipt(message_id=f"offline-{len(self.sent)}", thread_id=message.thread_id)

    def search(self, query: str, *, limit: int = 20) -> Sequence[Mapping[str, str]]:
        del query, limit
        return ()


class InMemoryCalendarClient:
    def __init__(self) -> None:
        self.events: dict[str, tuple[CalendarEvent, CalendarReceipt]] = {}

    def create_event(self, event: CalendarEvent) -> CalendarReceipt:
        key = event.idempotency_key or f"offline-{len(self.events) + 1}"
        existing = self.events.get(key)
        if existing:
            return existing[1]
        receipt = CalendarReceipt(event_id=key)
        self.events[key] = (event, receipt)
        return receipt

    def find_event(self, idempotency_key: str) -> CalendarReceipt | None:
        existing = self.events.get(idempotency_key)
        return existing[1] if existing else None
