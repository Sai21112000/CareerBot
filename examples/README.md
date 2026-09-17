# CLI examples

These commands define the intended CLI contract. Run them from the repository root after setup.
Use fictional example data only; replace it with a locally captured, terms-compliant job source.

## Inspect commands

```bash
uv run careerbot --help
```

## Triage a bounded list

```bash
CAREERBOT_EXECUTION_PROFILE=dry_run \
  uv run careerbot triage \
  --input examples/jobs.json \
  --max-jobs 10
```

`triage` performs heuristic ranking and deduplication; use the MCP `score_job` tool or `apply`
preparation path for model-backed fit scoring.

## Prepare one application for review

```bash
CAREERBOT_EXECUTION_PROFILE=review \
  uv run careerbot apply \
  --job examples/job.json
```

## Preview a weekly batch

```bash
CAREERBOT_EXECUTION_PROFILE=dry_run \
  uv run careerbot batch-apply \
  --queue examples/review_queue.json \
  --max-applications 5 \
  --max-minutes 90
```

## Sync follow-ups

```bash
CAREERBOT_EXECUTION_PROFILE=review \
  uv run careerbot follow-up sync \
  --limit 20 \
  --max-minutes 20
```

## Reconcile statuses

```bash
CAREERBOT_EXECUTION_PROFILE=dry_run \
  uv run careerbot reconcile \
  --limit 50 \
  --max-minutes 30
```

## Start the local MCP server

```bash
CAREERBOT_EXECUTION_PROFILE=dry_run uv run careerbot-mcp
```

Do not add secrets to these commands. Put local credentials in the gitignored `.env` file.
`follow-up sync` lists due local records, and `reconcile` reports readiness; neither performs a
complete remote synchronization in the current alpha release.
