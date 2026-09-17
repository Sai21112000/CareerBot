"""Validated runtime configuration."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class ExecutionProfile(StrEnum):
    DRY_RUN = "dry_run"
    REVIEW = "review"
    AUTO = "auto"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="CAREERBOT_",
        extra="ignore",
    )

    env: str = "development"
    execution_profile: ExecutionProfile = ExecutionProfile.DRY_RUN
    data_dir: Path = Path("data")
    snapshot_dir: Path = Path("snapshots")
    xai_api_key: SecretStr | None = None
    xai_model: str = "grok-4.6"
    mcp_auth_token: SecretStr | None = None
    airtable_pat: SecretStr | None = None
    airtable_base_id: str | None = None
    google_client_secret_file: Path | None = None
    max_jobs_per_run: int = Field(default=100, ge=1, le=100)
    max_applications_per_run: int = Field(default=10, ge=0, le=25)
    max_run_minutes: int = Field(default=30, ge=1, le=240)

    @property
    def master_resume_path(self) -> Path:
        return self.data_dir / "master_resume.tex"

    @property
    def application_log_path(self) -> Path:
        return self.data_dir / "applications_log.csv"

    @property
    def career_strategy_path(self) -> Path:
        return self.data_dir / "career_strategy.json"

    @property
    def strategy_snapshot_dir(self) -> Path:
        return self.data_dir / "strategy_snapshots"
