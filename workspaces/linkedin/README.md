# LinkedIn workspace

**Order:** 1 in daily platform sequence
**Airtable `source` values:** `linkedin`, `linkedin_apify`
**Created:** 2026-09-12T02:29:41.775679+07:00

Easy Apply and LinkedIn job posts. Use manual, human-paced collection and respect platform terms.

## Layout
- `queues/` — ready-to-apply / triage JSON for this platform only
- `apply_logs/` — per-session submit/handoff logs
- `harvest/` — platform harvest artifacts or pointers

## Rules
- Do not mix other platforms' applies into this workspace's active queue.
- Family PDF from `../../Resume/` via job-application skill.
- Never auto-submit; only when the operator approves.
- Hand off salary; never invent numbers.
