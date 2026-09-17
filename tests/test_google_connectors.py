from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from job_agent.communications import CalendarEvent, EmailMessage
from job_agent.google_connectors import GmailAPIClient, GoogleCalendarAPIClient


class Request:
    def __init__(self, result: dict[str, Any]) -> None:
        self.result = result

    def execute(self) -> dict[str, Any]:
        return self.result


class GmailService:
    def __init__(self) -> None:
        self.body: dict[str, Any] = {}

    def users(self) -> GmailService:
        return self

    def messages(self) -> GmailService:
        return self

    def drafts(self) -> GmailService:
        return self

    def send(self, **kwargs: Any) -> Request:
        self.body = kwargs["body"]
        return Request({"id": "message-1", "threadId": "thread-1"})

    def create(self, **kwargs: Any) -> Request:
        self.body = kwargs["body"]
        return Request({"id": "draft-1", "message": {"id": "message-2"}})

    def list(self, **kwargs: Any) -> Request:
        del kwargs
        return Request({"messages": [{"id": "alert-1", "threadId": "thread-2"}]})


class CalendarService:
    def __init__(self) -> None:
        self.items: list[dict[str, Any]] = []
        self.body: dict[str, Any] = {}

    def events(self) -> CalendarService:
        return self

    def list(self, **kwargs: Any) -> Request:
        del kwargs
        return Request({"items": self.items})

    def insert(self, **kwargs: Any) -> Request:
        self.body = kwargs["body"]
        return Request({"id": "event-1", "htmlLink": "https://calendar.example/event-1"})


def test_gmail_draft_send_and_search() -> None:
    service = GmailService()
    client = GmailAPIClient(service)
    message = EmailMessage("recruiter@example.com", "AI Engineer", "Evidence-backed note.")

    assert client.draft(message).message_id == "message-2"
    assert client.send(message).message_id == "message-1"
    assert service.body["raw"]
    assert client.search("from:jobs", limit=10)[0]["external_id"] == "alert-1"


def test_calendar_creation_is_idempotency_ready() -> None:
    service = CalendarService()
    client = GoogleCalendarAPIClient(service)
    starts = datetime(2026, 9, 9, 10, tzinfo=UTC)
    event = CalendarEvent(
        "Follow up",
        starts,
        starts + timedelta(minutes=30),
        idempotency_key="application-1",
    )

    receipt = client.create_event(event)

    assert receipt.event_id == "event-1"
    assert service.body["extendedProperties"]["private"]["careerbotKey"] == "application-1"
