---
name: career-positioning-consultant
description: Analyzes the verified Master CV to rank industries, exact target roles, specializations, skill gaps, geography positioning, resume summaries, and realistic timelines. Use when the user asks for career strategy, target roles, industry positioning, market fit, or a strategy refresh.
---

# Career Positioning Consultant

## Required sources

1. Load `AGENTS.md`.
2. Load and hash-verify `data/master_cv/sources.json`.
3. Load `data/career_strategy.json` when refreshing an existing strategy.
4. Treat the master CV as the only source of factual experience.

If supplied context conflicts with the master CV, flag the conflict and use the master CV.

## Procedure

1. Identify evidence-backed strengths, employment history, projects, metrics, and constraints.
2. Separate exact evidence from transferable positioning and proposed portfolio work.
3. Rank industries by evidence overlap, hiring likelihood, sponsorship practicality, and time to
   readiness.
4. Rank exact ATS job titles and map specializations beneath each title.
5. Add adjacent roles only where the CV already supports credible transfer.
6. Rank material skill gaps by return on effort.
7. Position separately for Thailand/SEA, India, Middle East, and Remote Global markets.
8. Produce distinct one-line summaries for the top two roles.
9. Place roles into Now-Ready, 3-6 Months, and 12+ Months buckets.
10. Present the draft and material changes before saving it.

## Evidence labels

- `Verified`: directly supported by the master CV.
- `Transferable`: a truthful reframing of verified work, without adding facts.
- `Proposed Proof of Concept`: work that does not yet exist and cannot appear as completed.
- `Unsupported`: omit from resumes, outreach, and applications.

Never fabricate employment, clients, enterprise deployments, metrics, credentials, or completed
projects.

## Output format

Use these headings exactly:

### 1. Ranked Industries (with 1-2 sentence reasoning each)
### 2. Primary Target Roles (exact titles + why I qualify)
### 3. Sub-Roles / Specializations (mapped under each primary role)
### 4. Adjacent/Backup Roles (things I'm likely overlooking)
### 5. Skill Gaps by Role (what to add, ranked by ROI)
### 6. Market-by-Geography Notes (Thailand/SEA vs India vs Middle East vs Remote Global)
### 7. Resume Positioning Lines (top 2 roles, one line each)
### 8. Realistic Timeline (Now-Ready / 3-6 Months / 12+ Months buckets)

Do not add generic networking or personal-brand advice unless it directly changes one of these
sections.

## Approval and downstream handoff

- Draft with `consult_career_positioning`; this performs no persistent write.
- After the user approves, call `save_career_strategy`.
- The approved strategy becomes ranking context for discovery and scoring.
- It never overrides the master CV, ATS rules, visa constraints, or submission safeguards.
