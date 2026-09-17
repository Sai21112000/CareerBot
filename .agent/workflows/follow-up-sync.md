# Follow-up sync

Goal: prepare or record due follow-ups without sending unreviewed messages.

## Bounds

- Default profile: `review`
- Maximum due records: 20
- Maximum elapsed time: 20 minutes
- Maximum outbound messages in `review`: 0

## Run

```bash
CAREERBOT_EXECUTION_PROFILE=review \
  uv run careerbot follow-up sync --limit 20 --max-minutes 20
```

1. Read ledger rows whose `follow_up_date` is due and whose status permits follow-up.
2. Deduplicate by application idempotency key and previously recorded message identifier.
3. Verify that each row references a confirmed submission before drafting.
4. Draft a concise message using only verified application and resume facts. Use the approved
   strategy's market framing for that role family without adding experience. Include the company,
   role, application date, and a clear request for status.
5. In `dry_run`, preview only. In `review`, present every message and recipient for approval. In
   `auto`, send only through an approved connector and only if prior consent and recipient identity
   are unambiguous.
6. Record the exact approved or sent content, timestamp, provider message identifier, and next
   follow-up date. Never store OAuth tokens or private unrelated message content.
7. Save the last processed idempotency key when a bound is reached. Report drafted, approved, sent,
   skipped, and failed counts.
8. Record aggregate reply and interview conversion by role family for the next
   `career-strategy-refresh`.
