Write a concise, professional cover letter for the job below.

Prompt version: {{prompt_version}}

Hard requirements:
- Use only facts supported by the supplied master source.
- Do not invent achievements, employers, dates, credentials, or technologies.
- Do not use em or en dashes.
- Prefer specific evidence already present in the source.
- Return one JSON object only with `body` and `prompt_version` keys.
- The body must be plain text, ready to submit.

Job:
{{job_json}}

Master source:
{{master_source}}
