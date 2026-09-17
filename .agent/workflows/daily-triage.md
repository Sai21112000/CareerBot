# Daily triage

Goal: produce a small, ranked review queue without submitting applications.

## Bounds

- Profile: `dry_run`
- Maximum jobs: 100
- Maximum elapsed time: 45 minutes
- Maximum applications submitted: 0
- Stop early on provider cost limits, authentication failure, or prohibited access

## Run

```bash
CAREERBOT_EXECUTION_PROFILE=dry_run \
  uv run careerbot triage --input examples/jobs.json --max-jobs 100 --max-minutes 45
```

1. Load the approved `data/career_strategy.json`, then load only the bounded input set and resume
   from the last unprocessed fingerprint.
2. Normalize and deduplicate by canonical URL plus company and role.
3. Prioritize the configured target market and employers with work-authorization support, then
   the strategy's ranked exact titles and specializations.
4. Score from verified resume evidence; flag missing skills and sponsorship uncertainty.
5. Queue `apply`, `apply_with_caveats`, and `skip` recommendations with concise reasoning.
6. End when either limit is reached. Save the cursor and report jobs seen, duplicates, errors, and
   the ranked review queue.
7. Retain aggregate title, industry, location, sponsorship, score, and outcome signals as input to
   the next `career-strategy-refresh`; do not let one job rewrite the approved strategy.

No tailored artifact or external record is required during triage.

## After triage (apply handoff)

When moving scored `apply` jobs into application prep or Easy Apply, follow
`.agent/workflows/weekly-batch-apply.md`: tailor a distinct resume per job (or matching
role family), upload to Drive, link in Airtable, then apply with that file only. Never reuse
one generic LinkedIn resume across the queue.

## Platform gate

Triage and apply for **one platform per run**, in order LinkedIn → JobsDB → other.
Cross-check Airtable before applying so the same job is not submitted on multiple sites.
When LinkedIn is done, notify the user before starting JobsDB or other websites.
