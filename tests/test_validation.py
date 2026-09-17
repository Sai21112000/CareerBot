from __future__ import annotations

import pytest

from job_agent.validation import (
    ArtifactValidationError,
    require_valid_tailored_resume,
    validate_ats_rules,
    validate_supported_claims,
    validate_supported_prose_claims,
)

MASTER = r"""
\documentclass{article}
\begin{document}
\section{Projects}
\item Built computer vision systems with Python and AWS.
\section{Thesis}
\item Oil palm instance segmentation using remote sensing.
\section{Education}
Asian Institute of Technology, May 2026
\end{document}
"""


def test_valid_trimmed_resume_is_supported() -> None:
    tailored = MASTER.replace(
        r"\item Built computer vision systems with Python and AWS." + "\n",
        "",
    )
    assert validate_ats_rules(tailored).valid
    assert validate_supported_claims(tailored, MASTER).valid
    require_valid_tailored_resume(tailored, MASTER)


def test_unsupported_claim_is_rejected() -> None:
    tailored = MASTER.replace(
        "computer vision systems",
        "award winning Kubernetes systems",
    )
    report = validate_supported_claims(tailored, MASTER)
    assert not report.valid
    assert "kubernetes" in report.errors[0]
    with pytest.raises(ArtifactValidationError):
        require_valid_tailored_resume(tailored, MASTER)


def test_unsupported_cover_letter_claim_is_rejected() -> None:
    supported = validate_supported_prose_claims(
        "I have experience with Python and AWS.",
        MASTER,
    )
    unsupported = validate_supported_prose_claims(
        "I managed Kubernetes for 50 enterprise clients.",
        MASTER,
    )
    assert supported.valid
    assert not unsupported.valid
    assert "kubernetes" in unsupported.errors[0]
    assert "50" in unsupported.errors[0]


@pytest.mark.parametrize(
    ("replacement", "expected"),
    [
        ("Proofs of Concept — production", "em/en dash"),
        ("POCs", "Proofs of Concept"),
        (r"\hrule", "decorative lines"),
        ("Feb - July 2026", "double hyphens"),
    ],
)
def test_deterministic_ats_rules(replacement: str, expected: str) -> None:
    report = validate_ats_rules(MASTER.replace("May 2026", replacement))
    assert any(expected in error for error in report.errors)


def test_projects_and_thesis_must_precede_education() -> None:
    reordered = r"""
\section{Education}
Asian Institute of Technology
\section{Projects}
Computer vision
\section{Thesis}
Remote sensing
"""
    errors = validate_ats_rules(reordered).errors
    assert "Projects must appear above Education" in errors
    assert "Thesis must appear above Education" in errors
