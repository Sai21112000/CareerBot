"""Composable career-positioning consultant operations."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from job_agent.scoring import load_master_cv_text
from job_agent.strategy import CareerStrategy, CareerStrategyStore, generate_career_strategy


def consult_career(
    master_cv_path: str | Path,
    *,
    llm: object,
    market_context: str = "",
    model: str | None = None,
) -> dict[str, Any]:
    """Generate a CV-grounded strategy for review without persisting it."""
    strategy = generate_career_strategy(
        load_master_cv_text(Path(master_cv_path)),
        llm,
        market_context=market_context,
        model=model,
    )
    return strategy.model_dump(mode="json")


def save_reviewed_strategy(
    strategy: CareerStrategy | dict[str, Any],
    *,
    current_path: str | Path = "data/career_strategy.json",
    snapshot_dir: str | Path = "data/strategy_snapshots",
) -> dict[str, str | None]:
    """Persist only a strategy the caller has explicitly reviewed."""
    parsed = (
        strategy
        if isinstance(strategy, CareerStrategy)
        else CareerStrategy.model_validate(strategy)
    )
    snapshot = CareerStrategyStore(Path(current_path), Path(snapshot_dir)).save(parsed)
    return {
        "current_path": str(current_path),
        "snapshot_path": str(snapshot),
        "source_hash": parsed.source_hash,
    }
