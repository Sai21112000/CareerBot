from __future__ import annotations

import json
from pathlib import Path

from job_agent.strategy import (
    CareerStrategyStore,
    generate_career_strategy,
    strategy_context,
)


def strategy_payload() -> dict[str, object]:
    return {
        "ranked_industries": [
            {
                "rank": 1,
                "industry": "Enterprise AI Consulting",
                "reasoning": "The verified CV shows governed agent and MCP delivery work.",
                "company_types": ["consultancy"],
            }
        ],
        "primary_target_roles": [
            {
                "rank": 1,
                "title": "Applied AI Engineer",
                "why_qualified": "The verified CV demonstrates LLM, RAG, MCP, and deployment work.",
                "specializations": ["AI Solutions Engineer", "LLM Engineer"],
                "company_types": ["consultancy", "enterprise"],
            },
            {
                "rank": 2,
                "title": "Computer Vision Engineer",
                "why_qualified": "The verified CV demonstrates detection and segmentation systems.",
                "specializations": ["Geospatial Computer Vision Engineer"],
                "company_types": ["product company"],
            },
        ],
        "adjacent_backup_roles": [
            {
                "rank": 1,
                "title": "AI Solutions Engineer",
                "why_qualified": "Client-facing delivery and infrastructure experience transfer.",
                "specializations": ["Technical Solutions Engineer"],
                "company_types": ["enterprise"],
            }
        ],
        "skill_gaps": [
            {
                "role_tier": "Applied AI Engineer",
                "gap": "Production evaluation portfolio",
                "roi_rank": 1,
                "action": "Publish one proposed evaluation-focused Proof of Concept.",
            }
        ],
        "market_by_geography": {
            "Thailand/SEA": "Lead with local delivery experience and work authorization needs.",
            "India": "Lead with applied AI delivery and computer vision depth.",
            "Middle East": "Emphasize enterprise AI solutions and governed deployment.",
            "Remote Global": "Emphasize reproducible public evidence and async delivery.",
        },
        "resume_positioning_lines": [
            {
                "target_role": "Applied AI Engineer",
                "line": (
                    "Applied AI Engineer building governed LLM agents "
                    "and enterprise retrieval systems."
                ),
            },
            {
                "target_role": "Computer Vision Engineer",
                "line": "Computer Vision Engineer delivering detection and segmentation systems.",
            },
        ],
        "realistic_timeline": {
            "Now-Ready": ["Applied AI Engineer", "Computer Vision Engineer"],
            "3-6 Months": ["Forward Deployed Engineer"],
            "12+ Months": ["Senior MLOps Engineer"],
        },
        "evidence_warnings": ["Do not claim proposed portfolio work as completed."],
    }


def test_generate_strategy_is_grounded_and_structured() -> None:
    master_cv = "Verified experience with LLM agents, MCP, and computer vision."
    strategy = generate_career_strategy(
        master_cv,
        lambda prompt: json.dumps(strategy_payload()),
        model="test-model",
    )

    assert strategy.model == "test-model"
    assert strategy.source_hash is not None
    assert "applied ai engineer" in strategy.target_terms()
    assert "primary_target_roles" in strategy_context(strategy)


def test_strategy_store_keeps_current_and_immutable_snapshot(tmp_path: Path) -> None:
    strategy = generate_career_strategy(
        "Verified CV.",
        lambda prompt: json.dumps(strategy_payload()),
    )
    store = CareerStrategyStore(
        tmp_path / "career_strategy.json",
        tmp_path / "strategy_snapshots",
    )

    snapshot = store.save(strategy)

    assert snapshot.is_file()
    assert not bool(snapshot.stat().st_mode & 0o222)
    assert store.load() == strategy
    assert store.save(strategy) == snapshot
