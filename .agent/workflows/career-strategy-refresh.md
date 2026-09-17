# Career strategy refresh

Goal: maintain one approved, evidence-backed strategy that guides every downstream CareerBot
workflow.

## Bounds

- Default profile: `review`
- Maximum representative jobs analyzed: 20
- Maximum elapsed time: 30 minutes
- Maximum model-generated strategy drafts: 2
- External applications or messages sent: 0

## Run

1. Load `AGENTS.md` and hash-verify all sources in `data/master_cv/sources.json`.
2. Load the current `data/career_strategy.json` when present.
3. Summarize new market evidence from up to 20 representative jobs and recent application
   outcomes. Do not scrape prohibited sources.
4. Call `consult_career_positioning` with the market evidence. The first result is a draft only.
5. Compare the draft with the current strategy:
   - promoted or demoted industries and roles
   - changed geography positioning
   - changed skill-gap priorities
   - changed Now-Ready, 3-6 Months, and 12+ Months buckets
   - unsupported claims or conflicts
6. Render the eight required consultant sections and show reasoning to the user.
7. If rejected, retain the current strategy unchanged.
8. If approved, call `save_career_strategy`; retain the immutable snapshot path and source hash.
9. Trigger downstream refreshes:
   - discovery: update role-title and specialization search terms
   - scoring: use approved priorities and geography notes as context
   - tailoring: select the matching approved positioning line
   - outreach: use employer-type and market framing
10. Report the approved strategy version, changes, evidence warnings, and affected workflows.

## Schedule

- Run once during initial setup.
- Refresh monthly, or earlier when 20 new applications, a material CV update, or a major visa or
  market change occurs.

The strategy may prioritize and frame verified evidence. It may not create new experience.
