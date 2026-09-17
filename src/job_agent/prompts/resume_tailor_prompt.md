You are tailoring an ATS-friendly LaTeX resume for the job below.

Prompt version: {{prompt_version}}

Hard requirements:
- The master resume is the only source of truth.
- Only remove, select, or reorder existing material. Do not invent, exaggerate, or add claims.
- Preserve the base LaTeX structure.
- Keep Projects and Thesis above Education.
- Use `Proofs of Concept`, never `POCs`.
- Use double hyphens for date ranges and never use em or en dashes.
- Do not add decorative lines.
- The result must compile to exactly one page.

Return one JSON object only with these keys:
`changes` (array of concise strings), `tailored_tex` (complete LaTeX document),
`resume_version_note` (concise string), and `prompt_version` (string).

Job:
{{job_json}}

Master resume:
{{master_resume}}
