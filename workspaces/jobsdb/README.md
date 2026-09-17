# JobsDB workspace

**Order:** 2 in daily platform sequence
**Airtable `source` values:** `jobsdb`
**Created:** 2026-09-12T02:29:41.775679+07:00

JobsDB workspace for manually collected jobs, permitted alerts, and approved integrations.

## Layout
- `queues/` — ready-to-apply / triage JSON for this platform only
- `apply_logs/` — per-session submit/handoff logs
- `harvest/` — platform harvest artifacts or pointers

## Rules
- Do not mix other platforms' applies into this workspace's active queue.
- Family PDF from `../../Resume/` via job-application skill.
- Never auto-submit; only when the operator approves.
- Hand off salary; never invent numbers.
