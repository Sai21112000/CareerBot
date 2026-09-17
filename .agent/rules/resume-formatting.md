---
description: Preserve verified resume content and ATS formatting
globs:
  - "data/**/*.tex"
  - "snapshots/**/*.tex"
alwaysApply: false
---

# Resume formatting

When creating or reviewing a tailored resume:

1. Treat `data/master_resume.tex` and the complete private master CV as the only factual sources.
2. Never invent, infer, exaggerate, or silently rewrite experience, dates, education, metrics,
   skills, titles, employers, publications, or project outcomes.
3. Tailor by selecting, trimming, and reordering verified content. Ask for approval before changing
   the base LaTeX structure.
4. Keep the tailored resume to one ATS-friendly page.
5. Keep Projects and Thesis above Education.
6. Use standardized capitalization throughout.
7. Use `Proofs of Concept`, never `POCs`, when referring to products or prototypes.
8. Use double hyphens in date ranges, for example `Feb -- July 2026`.
9. Never use em dashes or decorative lines.
10. Prefer plain section headings, conventional bullets, and text that remains readable when
    extracted from the PDF. Avoid columns, icons, text boxes, graphics, and important content in
    headers or footers.
11. Preserve valid LaTeX escaping and compile before finalizing when a LaTeX toolchain is available.
12. Present proposed content changes and their reasons for review before final user-facing copy.
13. Save an approved result as a new immutable snapshot. Do not overwrite an earlier finalized
    application artifact.
