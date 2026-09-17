from pathlib import Path

from job_agent.workflows import (
    BoundedWorkflow,
    CheckpointStore,
    RunLimits,
    WorkResult,
)


def test_workflow_is_bounded_and_resumes(tmp_path: Path) -> None:
    store = CheckpointStore(tmp_path / "checkpoint.json")
    calls: list[str] = []

    def process(item_id: str, value: int) -> WorkResult[int]:
        calls.append(item_id)
        return WorkResult(item_id, value, prepared=True, submitted=True)

    items = [("one", 1), ("two", 2), ("three", 3)]
    first = BoundedWorkflow(
        store, RunLimits(max_jobs=10, max_applications=1, max_minutes=1)
    ).run(items, process)
    assert first.applications_submitted == 1
    assert calls == ["one"]

    second = BoundedWorkflow(
        store, RunLimits(max_jobs=10, max_applications=2, max_minutes=1)
    ).run(items, process)
    assert second.applications_submitted == 3
    assert calls == ["one", "two", "three"]
    assert second.completed_at is not None


def test_workflow_deduplicates_item_ids(tmp_path: Path) -> None:
    calls: list[str] = []
    workflow = BoundedWorkflow(
        CheckpointStore(tmp_path / "checkpoint.json"),
        RunLimits(max_jobs=5, max_applications=5, max_minutes=1),
    )
    workflow.run(
        [("same", 1), ("same", 2)],
        lambda item_id, value: (
            calls.append(item_id) or WorkResult(item_id, value, prepared=True)
        ),
    )
    assert calls == ["same"]


def test_failed_item_remains_pending_for_resume(tmp_path: Path) -> None:
    store = CheckpointStore(tmp_path / "checkpoint.json")
    fail = True

    def process(item_id: str, value: int) -> WorkResult[int]:
        nonlocal fail
        if fail:
            fail = False
            raise RuntimeError("temporary")
        return WorkResult(item_id, value)

    workflow = BoundedWorkflow(
        store, RunLimits(max_jobs=1, max_applications=1, max_minutes=1)
    )
    first = workflow.run([("one", 1)], process)
    assert first.errors
    assert first.completed_at is None
    second = workflow.run([("one", 1)], process)
    assert second.jobs_seen == 1
