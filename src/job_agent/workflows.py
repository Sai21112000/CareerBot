"""Bounded, resumable workflow primitives."""

from __future__ import annotations

import json
import os
import tempfile
import time
import uuid
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from job_agent.models import RunManifest, utc_now


@dataclass(frozen=True)
class RunLimits:
    max_jobs: int = 20
    max_applications: int = 5
    max_minutes: float = 30

    def __post_init__(self) -> None:
        if self.max_jobs < 0 or self.max_applications < 0 or self.max_minutes <= 0:
            raise ValueError("workflow limits must be non-negative and time must be positive")


@dataclass
class WorkflowCheckpoint:
    run_id: str
    profile: str
    pending_ids: list[str] = field(default_factory=list)
    completed_ids: list[str] = field(default_factory=list)
    jobs_seen: int = 0
    applications_prepared: int = 0
    applications_submitted: int = 0
    handoffs: int = 0
    errors: list[str] = field(default_factory=list)
    completed_at: str | None = None


class CheckpointStore:
    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)

    def load(self) -> WorkflowCheckpoint | None:
        if not self.path.exists():
            return None
        return WorkflowCheckpoint(**json.loads(self.path.read_text(encoding="utf-8")))

    def save(self, checkpoint: WorkflowCheckpoint) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, name = tempfile.mkstemp(dir=self.path.parent, prefix=".workflow-", text=True)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(checkpoint.__dict__, handle, indent=2, sort_keys=True)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(name, self.path)
        except BaseException:
            Path(name).unlink(missing_ok=True)
            raise


@dataclass(frozen=True)
class WorkResult[T]:
    item_id: str
    value: T
    prepared: bool = False
    submitted: bool = False
    handoff: bool = False


class BoundedWorkflow[T]:
    """Processes identified items within count and wall-clock limits.

    A checkpoint is written after every item. Resuming skips completed IDs and retains
    pending IDs, making interruption safe without creating duplicate side effects.
    """

    def __init__(
        self,
        store: CheckpointStore,
        limits: RunLimits,
        *,
        profile: str = "dry_run",
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.store = store
        self.limits = limits
        self.profile = profile
        self.clock = clock

    def run(
        self,
        items: Iterable[tuple[str, T]],
        processor: Callable[[str, T], WorkResult[object]],
        *,
        resume: bool = True,
    ) -> RunManifest:
        checkpoint = self.store.load() if resume else None
        if checkpoint is None or checkpoint.completed_at is not None:
            checkpoint = WorkflowCheckpoint(run_id=uuid.uuid4().hex, profile=self.profile)

        completed = set(checkpoint.completed_ids)
        queue: list[tuple[str, T]] = []
        seen_ids: set[str] = set()
        for item_id, item in items:
            if item_id in completed or item_id in seen_ids:
                continue
            seen_ids.add(item_id)
            queue.append((item_id, item))
        checkpoint.pending_ids = [item_id for item_id, _ in queue]
        self.store.save(checkpoint)

        started = self.clock()
        processed_now = 0
        submitted_now = 0
        for item_id, item in queue:
            if processed_now >= self.limits.max_jobs:
                break
            if submitted_now >= self.limits.max_applications:
                break
            if self.clock() - started >= self.limits.max_minutes * 60:
                break
            processed_now += 1
            try:
                result = processor(item_id, item)
            except Exception as exc:
                checkpoint.errors.append(f"{item_id}: {type(exc).__name__}: {exc}")
                self.store.save(checkpoint)
                continue
            checkpoint.completed_ids.append(item_id)
            checkpoint.pending_ids.remove(item_id)
            checkpoint.jobs_seen += 1
            checkpoint.applications_prepared += int(result.prepared)
            checkpoint.applications_submitted += int(result.submitted)
            checkpoint.handoffs += int(result.handoff)
            submitted_now += int(result.submitted)
            self.store.save(checkpoint)

        if not checkpoint.pending_ids:
            checkpoint.completed_at = utc_now().isoformat()
            self.store.save(checkpoint)
        return checkpoint_to_manifest(checkpoint)


def checkpoint_to_manifest(checkpoint: WorkflowCheckpoint) -> RunManifest:
    return RunManifest(
        run_id=checkpoint.run_id,
        profile=checkpoint.profile,
        jobs_seen=checkpoint.jobs_seen,
        applications_prepared=checkpoint.applications_prepared,
        applications_submitted=checkpoint.applications_submitted,
        handoffs=checkpoint.handoffs,
        errors=checkpoint.errors,
        completed_at=(
            datetime.fromisoformat(checkpoint.completed_at) if checkpoint.completed_at else None
        ),
    )
