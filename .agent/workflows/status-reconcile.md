# Status reconcile

Goal: align the local ledger with explicit confirmation evidence while preserving an audit trail.

## Bounds

- Default profile: `dry_run`
- Maximum records: 50
- Maximum elapsed time: 30 minutes
- No form submissions or outbound messages

## Run

```bash
CAREERBOT_EXECUTION_PROFILE=dry_run \
  uv run careerbot reconcile --limit 50 --max-minutes 30
```

1. Load at most 50 non-terminal or recently changed ledger rows.
2. Compare local status with available confirmation IDs, approved mailbox events, or connector
   records. Access only accounts and data the user authorized.
3. Never infer `submitted` from a prepared snapshot, browser visit, or outbound draft. Require
   confirmation evidence.
4. Propose transitions with the evidence source and timestamp. Do not downgrade or overwrite
   conflicting evidence silently.
5. In `dry_run`, print the proposed changes. In `review`, require approval before local or external
   updates. In `auto`, apply only unambiguous supported transitions.
6. Route conflicting identity, missing evidence, authentication prompts, and provider ambiguity to
   manual review.
7. Preserve prior values in the audit record, update `updated_at`, and save a resume cursor at any
   bound. Report unchanged, proposed, updated, conflicted, and failed counts.
8. Aggregate status transitions by approved role family, industry, and geography as evidence for
   the next `career-strategy-refresh`; never change the strategy during reconciliation.
