# Weekly batch apply

Goal: queue a reviewable batch of high-fit applications using resume-family PDFs,
preserving verified facts and manual approval before any submit.

## Bounds

- Default profile: `review`
- Maximum queued jobs: 10
- Maximum applications prepared or submitted: 5
- Maximum elapsed time: 90 minutes
- Never auto-submit without explicit operator approval of the job or named batch

## Resume input

- Family PDFs in `Resume/` (see `AGENTS.md` mapping)
- Classifier: `.agent/skills/job-application/SKILL.md`
- Load approved `data/career_strategy.json` when present
- Stop if the mapped family PDF is missing

## Run

```bash
CAREERBOT_EXECUTION_PROFILE=review \
  CAREERBOT_MAX_APPLICATIONS_PER_RUN=5 \
  uv run careerbot batch-apply --queue examples/review_queue.json --max-minutes 90
```

1. Load career strategy and confirm `Resume/` family PDFs exist.
2. Select no more than 10 reviewed jobs, highest fit first, with the configured priority market
   and work-authorization support as tie-breakers.
3. Skip duplicates already marked `submitted`. Resume prepared records from their snapshot.
4. For each job, run the job-application skill: assign exactly one `resume_family`,
   secondary tags, seniority, suitability, match score, and classification reason.
5. Map `resume_family` → the corresponding PDF under `Resume/`. Do **not** generate a
   per-job LaTeX resume, cover letter, or Drive package. Mark ready when classification
   + family PDF path are recorded in Airtable (optional note of which PDF).
6. Draft only evidence-backed form answers. Route legal, demographic, salary, sponsorship,
   consent, and declaration questions to the user when no approved answer exists.
7. In `review`, stop at approval. Never click Easy Apply / portal Submit until the operator
   explicitly approves that job or batch.
8. On approval, upload/use the **selected family PDF**. Prefer it over LinkedIn's default
   resume. Log source URL, answers, family PDF filename, and confirmation evidence.
9. Mark `submitted` only with confirmation evidence.
10. Stop immediately at any bound and save a resume cursor. Report classified, queued,
    submitted, handed off, skipped, and failed counts.
11. Feed aggregate conversion by resume family, industry, and geography into the next
    `career-strategy-refresh`.

## LinkedIn Easy Apply (authorized sessions)

When the operator has authorized applies for a named set of jobs and a signed-in LinkedIn
browser session exists:

1. Classify each target with `.agent/skills/job-application/SKILL.md`.
2. Select the matching family PDF from `Resume/` (reuse within a family is expected).
3. Do not create per-job tailored packages or require Drive `resume_drive_url` uploads.
4. Apply only jobs in the approved set; upload that family's PDF when a file is required.
5. Update Airtable Applications/Jobs for every attempt with confirmation evidence and which
   family PDF was used.
6. Hand off CAPTCHA, MFA, declarations, and unanswered legal/sponsorship/salary questions.

## Priority and salary handoff

1. Prefer jobs/companies with confirmed or likely work-authorization support in the configured
   priority market before companies that do not mention sponsorship.
2. Always hand off any current/expected salary field. Never invent numbers.
3. Optimize for interview invites; user handles sponsorship and compensation negotiation.

## One platform at a time

Apply on a single platform per run (LinkedIn → JobsDB → other). Deduplicate against
Airtable Applications across sites. After finishing LinkedIn, notify the user and wait
before JobsDB or other portals.
