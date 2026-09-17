"""Career-positioning strategy generation and immutable persistence."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from job_agent.tailoring import extract_structured_output, invoke_llm

PROMPT_VERSION = "1.0.0"
PROMPT_PATH = Path(__file__).with_name("prompts") / "career_consultant_prompt.md"


class RankedIndustry(BaseModel):
    rank: int = Field(ge=1)
    industry: str = Field(min_length=2)
    reasoning: str = Field(min_length=10)
    company_types: list[str] = Field(default_factory=list)


class TargetRole(BaseModel):
    rank: int = Field(ge=1)
    title: str = Field(min_length=2)
    why_qualified: str = Field(min_length=10)
    specializations: list[str] = Field(default_factory=list)
    company_types: list[str] = Field(default_factory=list)


class SkillGap(BaseModel):
    role_tier: str = Field(min_length=2)
    gap: str = Field(min_length=2)
    roi_rank: int = Field(ge=1)
    action: str = Field(min_length=5)


class ResumePositioningLine(BaseModel):
    target_role: str = Field(min_length=2)
    line: str = Field(min_length=10)


class CareerStrategy(BaseModel):
    ranked_industries: list[RankedIndustry]
    primary_target_roles: list[TargetRole]
    adjacent_backup_roles: list[TargetRole]
    skill_gaps: list[SkillGap]
    market_by_geography: dict[str, str]
    resume_positioning_lines: list[ResumePositioningLine]
    realistic_timeline: dict[str, list[str]]
    evidence_warnings: list[str] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    prompt_version: str = PROMPT_VERSION
    model: str | None = None
    source_hash: str | None = None

    def target_terms(self) -> tuple[str, ...]:
        terms: list[str] = []
        for role in self.primary_target_roles:
            terms.append(role.title)
            terms.extend(role.specializations)
        return tuple(dict.fromkeys(term.casefold() for term in terms if term.strip()))


def generate_career_strategy(
    master_cv_text: str,
    llm: object,
    *,
    market_context: str = "",
    model: str | None = None,
) -> CareerStrategy:
    """Generate a validated strategy grounded in the hash-verified master CV."""
    if not master_cv_text.strip():
        raise ValueError("master CV text is required")
    prompt = (
        PROMPT_PATH.read_text(encoding="utf-8")
        .replace("{{master_cv_text}}", master_cv_text)
        .replace("{{market_context}}", market_context or "No additional market context supplied.")
    )
    parsed = CareerStrategy.model_validate(extract_structured_output(invoke_llm(llm, prompt)))
    return parsed.model_copy(
        update={
            "prompt_version": PROMPT_VERSION,
            "model": model,
            "source_hash": hashlib.sha256(master_cv_text.encode("utf-8")).hexdigest(),
        }
    )


class CareerStrategyStore:
    """Maintain a current strategy plus immutable timestamped snapshots."""

    def __init__(self, current_path: Path, snapshot_dir: Path) -> None:
        self.current_path = current_path
        self.snapshot_dir = snapshot_dir

    def load(self) -> CareerStrategy | None:
        if not self.current_path.is_file():
            return None
        return CareerStrategy.model_validate_json(
            self.current_path.read_text(encoding="utf-8")
        )

    def save(self, strategy: CareerStrategy) -> Path:
        payload = (
            json.dumps(strategy.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"
        )
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]
        timestamp = strategy.generated_at.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)
        snapshot = self.snapshot_dir / f"{timestamp}-{digest}.json"
        if snapshot.exists():
            existing = snapshot.read_text(encoding="utf-8")
            if existing != payload:
                raise ValueError(f"strategy snapshot collision: {snapshot}")
        else:
            snapshot.write_text(payload, encoding="utf-8")
            snapshot.chmod(0o444)

        self.current_path.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(
            dir=self.current_path.parent,
            prefix=".career-strategy-",
            suffix=".json",
            text=True,
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, self.current_path)
        except BaseException:
            Path(temporary).unlink(missing_ok=True)
            raise
        return snapshot


def strategy_context(strategy: CareerStrategy | None) -> str:
    """Serialize only the downstream fields needed by scoring and discovery."""
    if strategy is None:
        return ""
    payload: dict[str, Any] = {
        "primary_target_roles": [
            {
                "title": role.title,
                "rank": role.rank,
                "specializations": role.specializations,
            }
            for role in strategy.primary_target_roles
        ],
        "adjacent_backup_roles": [role.title for role in strategy.adjacent_backup_roles],
        "market_by_geography": strategy.market_by_geography,
        "realistic_timeline": strategy.realistic_timeline,
    }
    return json.dumps(payload, sort_keys=True)
