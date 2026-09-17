"""Deterministic validation for generated application artifacts."""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass


class ArtifactValidationError(ValueError):
    """Raised when a generated artifact violates a deterministic rule."""

    def __init__(self, errors: Iterable[str]) -> None:
        self.errors = tuple(errors)
        super().__init__("; ".join(self.errors))


@dataclass(frozen=True)
class ValidationReport:
    errors: tuple[str, ...] = ()

    @property
    def valid(self) -> bool:
        return not self.errors

    def raise_for_errors(self) -> None:
        if self.errors:
            raise ArtifactValidationError(self.errors)


_LATEX_COMMAND = re.compile(r"\\[a-zA-Z@]+\*?(?:\[[^\]]*\])?")
_LATEX_COMMENT = re.compile(r"(?<!\\)%.*$")
_WORD = re.compile(r"[A-Za-z][A-Za-z0-9+#./-]*|\d+(?:[.,]\d+)*%?")
_DATE_RANGE = re.compile(
    r"\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|June?|July?|"
    r"Aug(?:ust)?|Sept?(?:ember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?|\d{4})"
    r"\s+[-–—]\s+"
    r"(?:Present|Current|Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|"
    r"June?|July?|Aug(?:ust)?|Sept?(?:ember)?|Oct(?:ober)?|Nov(?:ember)?|"
    r"Dec(?:ember)?|\d{4})\b"
)
_STRUCTURAL_WORDS = {
    "begin",
    "document",
    "end",
    "itemize",
    "enumerate",
    "center",
    "flushleft",
    "flushright",
    "tabular",
    "tabularx",
    "minipage",
    "par",
    "small",
    "footnotesize",
    "large",
    "vspace",
    "hspace",
    "noindent",
    "linewidth",
    "textwidth",
    "href",
    "url",
    "leftmargin",
    "itemsep",
    "topsep",
    "parsep",
    "parskip",
    "textbullet",
}
_PROSE_ALLOWLIST = {
    "am",
    "application",
    "apply",
    "applying",
    "background",
    "believe",
    "candidate",
    "contribute",
    "dear",
    "discuss",
    "excited",
    "experience",
    "fit",
    "hello",
    "hiring",
    "interest",
    "interested",
    "look",
    "looking",
    "opportunity",
    "position",
    "regards",
    "role",
    "sincerely",
    "strong",
    "team",
    "thank",
    "thanks",
    "would",
}
_CLAIM_STOPWORDS = {
    "a",
    "an",
    "and",
    "as",
    "at",
    "by",
    "for",
    "from",
    "had",
    "has",
    "have",
    "i",
    "in",
    "into",
    "me",
    "my",
    "of",
    "on",
    "or",
    "our",
    "the",
    "to",
    "we",
    "with",
}


def _plain_text(tex: str) -> str:
    lines = (_LATEX_COMMENT.sub("", line) for line in tex.splitlines())
    text = "\n".join(lines)
    text = re.sub(r"\\(?:begin|end)\{[^}]+\}", " ", text)
    text = _LATEX_COMMAND.sub(" ", text)
    text = re.sub(r"[{}&~_^$]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _claim_tokens(tex: str) -> set[str]:
    tokens = {token.casefold().strip("./-") for token in _WORD.findall(_plain_text(tex))}
    return {
        token
        for token in tokens
        if token and token not in _CLAIM_STOPWORDS and token not in _STRUCTURAL_WORDS
    }


def validate_ats_rules(tex: str) -> ValidationReport:
    """Validate project-specific ATS rules without invoking an LLM."""
    errors: list[str] = []
    if not tex.strip():
        errors.append("resume is empty")
        return ValidationReport(tuple(errors))
    if "—" in tex or "–" in tex:
        errors.append("resume contains an em/en dash; use double hyphens")
    if re.search(r"\bPOCs?\b", tex, re.IGNORECASE):
        errors.append("use 'Proofs of Concept', never 'POCs'")
    if re.search(r"\\(?:hline|hrule|rule)\b", tex):
        errors.append("decorative lines are not allowed")
    if _DATE_RANGE.search(_plain_text(tex)):
        errors.append("date ranges must use double hyphens")

    headings = {
        match.group(1).strip().casefold(): match.start()
        for match in re.finditer(r"\\(?:section|section\*)\{([^}]+)\}", tex)
    }
    education = headings.get("education")
    if education is not None:
        for required in ("projects", "thesis"):
            position = headings.get(required)
            if position is not None and position > education:
                errors.append(f"{required.title()} must appear above Education")
    return ValidationReport(tuple(errors))


def validate_supported_claims(tailored_tex: str, master_tex: str) -> ValidationReport:
    """Reject factual vocabulary absent from the master source.

    Tailoring is intentionally trim-and-reorder only. LaTeX structure and common
    connective words are ignored, while claim-bearing words, numbers, and skills
    must already occur in the master resume.
    """
    if not master_tex.strip():
        return ValidationReport(("master resume source is empty",))
    master_tokens = _claim_tokens(master_tex)
    unsupported = sorted(_claim_tokens(tailored_tex) - master_tokens)
    if not unsupported:
        return ValidationReport()
    preview = ", ".join(unsupported[:12])
    suffix = "" if len(unsupported) <= 12 else f" (+{len(unsupported) - 12} more)"
    return ValidationReport((f"unsupported claims or terms: {preview}{suffix}",))


def validate_supported_prose_claims(body: str, master_source: str) -> ValidationReport:
    """Check first-person cover-letter claims against the master source."""
    supported = _claim_tokens(master_source) | _PROSE_ALLOWLIST
    unsupported: set[str] = set()
    for sentence in re.split(r"(?<=[.!?])\s+|\n+", body):
        if not re.search(r"\b(?:I|I've|I’m|my|me)\b", sentence, re.IGNORECASE):
            continue
        unsupported.update(_claim_tokens(sentence) - supported)
    if not unsupported:
        return ValidationReport()
    preview = ", ".join(sorted(unsupported)[:12])
    return ValidationReport((f"unsupported cover-letter claims or terms: {preview}",))


def validate_tailored_resume(tailored_tex: str, master_tex: str) -> ValidationReport:
    errors = (
        validate_ats_rules(tailored_tex).errors
        + validate_supported_claims(tailored_tex, master_tex).errors
    )
    return ValidationReport(errors)


def require_valid_tailored_resume(tailored_tex: str, master_tex: str) -> None:
    validate_tailored_resume(tailored_tex, master_tex).raise_for_errors()
