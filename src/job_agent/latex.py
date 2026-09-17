"""Optional, bounded LaTeX compilation using Tectonic."""

from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader


class LatexCompilationError(RuntimeError):
    """Raised when Tectonic fails or the resume exceeds one page."""


@dataclass(frozen=True)
class CompilationResult:
    attempted: bool
    pdf_path: Path | None
    page_count: int | None
    log: str = ""


def tectonic_available() -> bool:
    return shutil.which("tectonic") is not None


def pdf_page_count(path: Path) -> int:
    """Count pages through the PDF object graph, including compressed objects."""
    try:
        count = len(PdfReader(path).pages)
    except Exception as exc:
        raise LatexCompilationError(f"unable to determine page count for {path}") from exc
    if count < 1:
        raise LatexCompilationError(f"compiled PDF has no pages: {path}")
    return count


def compile_latex(
    tex: str,
    output_dir: Path,
    *,
    stem: str = "resume",
    require_one_page: bool = True,
    timeout_seconds: int = 60,
) -> CompilationResult:
    """Compile when Tectonic is installed; otherwise return an unattempted result."""
    executable = shutil.which("tectonic")
    if executable is None:
        return CompilationResult(attempted=False, pdf_path=None, page_count=None)
    if not tex.strip():
        raise LatexCompilationError("cannot compile empty LaTeX")

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="careerbot-tex-") as temporary:
        source = Path(temporary) / f"{stem}.tex"
        source.write_text(tex, encoding="utf-8")
        command = [
            executable,
            "--keep-logs",
            "--outdir",
            str(output_dir),
            str(source),
        ]
        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                check=False,
                text=True,
                timeout=timeout_seconds,
            )
        except subprocess.TimeoutExpired as exc:
            raise LatexCompilationError(
                f"Tectonic exceeded {timeout_seconds} second timeout"
            ) from exc

    log = "\n".join(part for part in (completed.stdout, completed.stderr) if part).strip()
    pdf_path = output_dir / f"{stem}.pdf"
    if completed.returncode != 0 or not pdf_path.is_file():
        raise LatexCompilationError(
            f"Tectonic failed with exit code {completed.returncode}: {log[-2000:]}"
        )
    pages = pdf_page_count(pdf_path)
    if require_one_page and pages != 1:
        pdf_path.unlink(missing_ok=True)
        raise LatexCompilationError(f"resume must be exactly one page; compiled PDF has {pages}")
    return CompilationResult(attempted=True, pdf_path=pdf_path, page_count=pages, log=log)


def compile_one_page_resume(
    tex: str,
    output_dir: Path,
    *,
    stem: str = "resume",
    timeout_seconds: int = 60,
) -> CompilationResult:
    return compile_latex(
        tex,
        output_dir,
        stem=stem,
        require_one_page=True,
        timeout_seconds=timeout_seconds,
    )


def escape_latex(text: str) -> str:
    """Escape plain generated prose for safe insertion into a LaTeX document."""
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(replacements.get(character, character) for character in text)


def cover_letter_document(body: str) -> str:
    """Wrap plain cover-letter paragraphs in a minimal ATS-friendly document."""
    paragraphs = "\n\n".join(
        escape_latex(paragraph.strip())
        for paragraph in re.split(r"\n\s*\n", body)
        if paragraph.strip()
    )
    return (
        "\\documentclass[11pt]{article}\n"
        "\\usepackage[margin=1in]{geometry}\n"
        "\\usepackage[T1]{fontenc}\n"
        "\\pagestyle{empty}\n"
        "\\setlength{\\parindent}{0pt}\n"
        "\\setlength{\\parskip}{0.8em}\n"
        "\\begin{document}\n"
        f"{paragraphs}\n"
        "\\end{document}\n"
    )
