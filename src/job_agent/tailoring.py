"""LLM-assisted artifact generation with injectable model clients."""

from __future__ import annotations

import inspect
import json
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Protocol

from pydantic import BaseModel, ValidationError

from job_agent.latex import compile_one_page_resume
from job_agent.models import CoverLetterResult, Job, TailoringResult
from job_agent.validation import (
    ArtifactValidationError,
    require_valid_tailored_resume,
    validate_supported_prose_claims,
)

PROMPT_DIR = Path(__file__).with_name("prompts")


class GenerationError(RuntimeError):
    """Raised when model output cannot be converted to a valid artifact."""


class LLMGenerator(Protocol):
    def __call__(self, prompt: str) -> object: ...


def load_prompt(name: str) -> str:
    path = PROMPT_DIR / name
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        raise GenerationError(f"unable to load prompt {name!r}: {exc}") from exc


def render_prompt(name: str, **values: object) -> str:
    prompt = load_prompt(name)
    for key, value in values.items():
        prompt = prompt.replace("{{" + key + "}}", str(value))
    unresolved = [part.split("}}", 1)[0] for part in prompt.split("{{")[1:] if "}}" in part]
    if unresolved:
        raise GenerationError(f"unresolved prompt variables: {', '.join(sorted(unresolved))}")
    return prompt


def _response_text(response: object) -> str:
    if isinstance(response, str):
        return response
    if isinstance(response, bytes):
        return response.decode("utf-8")
    if isinstance(response, Mapping):
        for key in ("output_text", "content", "text", "response"):
            value = response.get(key)
            if isinstance(value, str):
                return value
    for attribute in ("output_text", "content", "text"):
        value = getattr(response, attribute, None)
        if isinstance(value, str):
            return value
    raise GenerationError("LLM returned no textual content")


def invoke_llm(llm: object, prompt: str) -> str:
    """Invoke a supplied callable or a client exposing invoke/generate/complete."""
    if callable(llm):
        response = llm(prompt)
    else:
        method = next(
            (
                getattr(llm, name)
                for name in ("invoke", "generate", "complete")
                if callable(getattr(llm, name, None))
            ),
            None,
        )
        if method is None:
            raise TypeError("llm must be callable or expose invoke, generate, or complete")
        response = method(prompt)
    if inspect.isawaitable(response):
        raise TypeError("async LLM supplied to synchronous generator")
    return _response_text(response)


def extract_structured_output(text: str) -> dict[str, Any]:
    """Extract the first JSON object, tolerating prose and fenced responses."""
    decoder = json.JSONDecoder()
    starts = [index for index, character in enumerate(text) if character == "{"]
    errors: list[str] = []
    for start in starts:
        try:
            value, _ = decoder.raw_decode(text[start:])
        except json.JSONDecodeError as exc:
            errors.append(str(exc))
            continue
        if isinstance(value, dict):
            return value
    detail = f": {errors[-1]}" if errors else ""
    raise GenerationError(f"LLM output did not contain a JSON object{detail}")


def _parse_result(model_type: type[BaseModel], text: str) -> BaseModel:
    try:
        return model_type.model_validate(extract_structured_output(text))
    except ValidationError as exc:
        raise GenerationError(f"invalid structured LLM output: {exc}") from exc


def tailor_resume(
    job: Job,
    master_tex: str,
    llm: LLMGenerator | object,
    *,
    prompt_version: str = "1.0.0",
    compilation_output_dir: Path | None = None,
) -> TailoringResult:
    prompt = render_prompt(
        "resume_tailor_prompt.md",
        job_json=job.model_dump_json(indent=2),
        master_resume=master_tex,
        prompt_version=prompt_version,
    )
    result = _parse_result(TailoringResult, invoke_llm(llm, prompt))
    assert isinstance(result, TailoringResult)
    result.prompt_version = prompt_version
    try:
        require_valid_tailored_resume(result.tailored_tex, master_tex)
    except ArtifactValidationError as exc:
        raise GenerationError(f"tailored resume failed validation: {exc}") from exc
    if compilation_output_dir is not None:
        compile_one_page_resume(result.tailored_tex, compilation_output_dir)
    else:
        with tempfile.TemporaryDirectory(prefix="careerbot-validate-") as temporary:
            compile_one_page_resume(result.tailored_tex, Path(temporary))
    return result


def generate_cover_letter(
    job: Job,
    master_source: str,
    llm: LLMGenerator | object,
    *,
    prompt_version: str = "1.0.0",
) -> CoverLetterResult:
    prompt = render_prompt(
        "cover_letter_prompt.md",
        job_json=job.model_dump_json(indent=2),
        master_source=master_source,
        prompt_version=prompt_version,
    )
    result = _parse_result(CoverLetterResult, invoke_llm(llm, prompt))
    assert isinstance(result, CoverLetterResult)
    result.prompt_version = prompt_version
    if "—" in result.body or "–" in result.body:
        raise GenerationError("cover letter contains an em/en dash")
    if not result.body.strip():
        raise GenerationError("cover letter is empty")
    report = validate_supported_prose_claims(
        result.body,
        f"{master_source}\n{job.company}\n{job.role}",
    )
    if not report.valid:
        raise GenerationError(f"cover letter failed validation: {'; '.join(report.errors)}")
    return result


def generate_snapshot_note(
    context: Mapping[str, object],
    llm: LLMGenerator | object,
) -> str:
    prompt = render_prompt(
        "snapshot_note_prompt.md",
        context_json=json.dumps(context, indent=2, default=str, sort_keys=True),
    )
    text = invoke_llm(llm, prompt).strip()
    if text.startswith("```") and text.endswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    if not text:
        raise GenerationError("snapshot note is empty")
    if "—" in text or "–" in text:
        raise GenerationError("snapshot note contains an em/en dash")
    return text
