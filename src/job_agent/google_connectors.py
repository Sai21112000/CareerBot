"""Thin Google API adapters built around injected authenticated service objects."""

from __future__ import annotations

import base64
from collections.abc import Mapping, Sequence
from email.message import EmailMessage as MIMEMessage
from typing import Any

from job_agent.communications import (
    CalendarEvent,
    CalendarReceipt,
    EmailMessage,
    EmailReceipt,
)


class GmailAPIClient:
    """Create drafts, send messages, and read authorized alert metadata."""

    def __init__(self, service: Any, *, user_id: str = "me") -> None:
        self.service = service
        self.user_id = user_id

    @staticmethod
    def _raw(message: EmailMessage) -> str:
        mime = MIMEMessage()
        mime["To"] = message.recipient
        mime["Subject"] = message.subject
        mime.set_content(message.body)
        if message.thread_id:
            mime["In-Reply-To"] = message.thread_id
        return base64.urlsafe_b64encode(mime.as_bytes()).decode()

    def draft(self, message: EmailMessage) -> EmailReceipt:
        result = (
            self.service.users()
            .drafts()
            .create(
                userId=self.user_id,
                body={"message": {"raw": self._raw(message), "threadId": message.thread_id}},
            )
            .execute()
        )
        payload = result.get("message", result)
        return EmailReceipt(
            message_id=str(payload.get("id", result.get("id", ""))),
            thread_id=payload.get("threadId"),
        )

    def send(self, message: EmailMessage) -> EmailReceipt:
        result = (
            self.service.users()
            .messages()
            .send(
                userId=self.user_id,
                body={"raw": self._raw(message), "threadId": message.thread_id},
            )
            .execute()
        )
        return EmailReceipt(
            message_id=str(result["id"]),
            thread_id=result.get("threadId"),
        )

    def search(self, query: str, *, limit: int = 20) -> Sequence[Mapping[str, str]]:
        result = (
            self.service.users()
            .messages()
            .list(userId=self.user_id, q=query, maxResults=min(limit, 100))
            .execute()
        )
        return tuple(
            {"external_id": str(item["id"]), "thread_id": str(item.get("threadId", ""))}
            for item in result.get("messages", [])
        )


class GoogleCalendarAPIClient:
    """Idempotently create follow-up or interview events."""

    def __init__(self, service: Any, *, calendar_id: str = "primary") -> None:
        self.service = service
        self.calendar_id = calendar_id

    def find_event(self, idempotency_key: str) -> CalendarReceipt | None:
        result = (
            self.service.events()
            .list(
                calendarId=self.calendar_id,
                privateExtendedProperty=f"careerbotKey={idempotency_key}",
                maxResults=1,
                singleEvents=True,
            )
            .execute()
        )
        items = result.get("items", [])
        if not items:
            return None
        item = items[0]
        return CalendarReceipt(event_id=str(item["id"]), html_link=item.get("htmlLink"))

    def create_event(self, event: CalendarEvent) -> CalendarReceipt:
        if event.idempotency_key:
            existing = self.find_event(event.idempotency_key)
            if existing is not None:
                return existing
        body: dict[str, Any] = {
            "summary": event.title,
            "description": event.description,
            "start": {"dateTime": event.starts_at.isoformat()},
            "end": {"dateTime": event.ends_at.isoformat()},
            "attendees": [{"email": address} for address in event.attendees],
        }
        if event.idempotency_key:
            body["extendedProperties"] = {
                "private": {"careerbotKey": event.idempotency_key}
            }
        result = (
            self.service.events()
            .insert(calendarId=self.calendar_id, body=body, sendUpdates="none")
            .execute()
        )
        return CalendarReceipt(
            event_id=str(result["id"]),
            html_link=result.get("htmlLink"),
        )
