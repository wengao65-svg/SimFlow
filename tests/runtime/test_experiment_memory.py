"""Cross-session tests for the forward-only experiment ledger."""

from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).parents[2]))

from runtime.simflow_core.checkpoints import create_checkpoint, restore_checkpoint
from runtime.simflow_core.experiment_memory import (
    begin_experiment,
    begin_iteration,
    build_reentry_summary,
    evaluate_iteration,
    finish_activity,
    is_ledger_enabled,
    project_reentry,
    session_handoff,
    start_activity,
    validate_session_context,
)
from runtime.simflow_core.state import init_workflow, resolve_project_root


def _open_experiment(tmp_path: Path):
    init_workflow("custom", "computation", project_root=str(tmp_path))
    entry = project_reentry(str(tmp_path), working_directory=str(tmp_path))
    experiment = begin_experiment(
        str(tmp_path),
        session_context_id=entry["session_context_id"],
        title="Iterative convergence",
        objective="Repeat calculations until the target metric passes",
        stage="computation",
        root_path="run",
        recipe="custom",
        acceptance_criteria=[{"description": "error below threshold", "metric": "error", "operator": "<", "threshold": 0.1}],
        next_action="start round one",
    )
    return entry, experiment


def test_reentry_does_not_import_legacy_state(tmp_path):
    init_workflow("custom", "computation", project_root=str(tmp_path))
    legacy = tmp_path / ".simflow" / "state" / "artifacts.json"
    legacy.write_text('[{"artifact_id":"art_legacy00"}]\n', encoding="utf-8")

    entry = project_reentry(str(tmp_path))

    assert entry["ledger"]["status"] == "not_started"
    assert entry["ledger"]["legacy_history_not_imported"] is True
    assert entry["active_experiments"] == []
    assert not is_ledger_enabled(str(tmp_path))


def test_new_session_recovers_iteration_failure_and_next_action(tmp_path):
    (tmp_path / "run").mkdir()
    entry, experiment = _open_experiment(tmp_path)
    iteration = begin_iteration(
        str(tmp_path),
        session_context_id=entry["session_context_id"],
        experiment_id=experiment["experiment_id"],
        objective="Round one",
        acceptance_criteria=["error below threshold"],
        next_action="run solver",
    )
    activity = start_activity(
        str(tmp_path),
        session_context_id=entry["session_context_id"],
        experiment_id=experiment["experiment_id"],
        iteration_id=iteration["iteration_id"],
        objective="Run solver",
        activity_type="computation",
        stage="computation",
        software="solver",
        version="1.2.3",
        command="solver --token=secret-value input.in",
    )
    finish_activity(
        str(tmp_path),
        session_context_id=entry["session_context_id"],
        experiment_id=experiment["experiment_id"],
        activity_id=activity["activity_id"],
        status="failed",
        failure={"reason": "did not converge"},
        restart_from={"path": "run/restart.dat", "checkpoint_id": "ckpt_good"},
        next_action="adjust mixing and repeat round two",
    )
    evaluate_iteration(
        str(tmp_path),
        session_context_id=entry["session_context_id"],
        experiment_id=experiment["experiment_id"],
        iteration_id=iteration["iteration_id"],
        status="failed",
        criterion_results=[{"criterion_id": "criterion_001", "status": "fail", "value": 0.4}],
        decision="continue with changed mixing",
        recovery={"path": "run/restart.dat", "checkpoint_id": "ckpt_good"},
        next_action="adjust mixing and repeat round two",
    )

    new_entry = project_reentry(str(tmp_path), experiment_id=experiment["experiment_id"])

    assert new_entry["current_iteration"]["iteration_id"] == iteration["iteration_id"]
    assert new_entry["latest_failure"]["activity_id"] == activity["activity_id"]
    assert new_entry["latest_recovery"]["checkpoint_id"] == "ckpt_good"
    assert new_entry["next_action"] == "adjust mixing and repeat round two"
    events = (tmp_path / ".simflow" / "memory" / "activity_events.jsonl").read_text(encoding="utf-8")
    assert "secret-value" not in events
    assert "[REDACTED]" in events


def test_interrupted_activity_is_visible_without_handoff(tmp_path):
    (tmp_path / "run").mkdir()
    entry, experiment = _open_experiment(tmp_path)
    activity = start_activity(
        str(tmp_path),
        session_context_id=entry["session_context_id"],
        experiment_id=experiment["experiment_id"],
        objective="Long running analysis",
        activity_type="analysis",
        stage="analysis_visualization",
    )

    summary = build_reentry_summary(str(tmp_path), experiment_id=experiment["experiment_id"])

    assert [item["activity_id"] for item in summary["interrupted_activities"]] == [activity["activity_id"]]


def test_latest_completed_activity_uses_finish_order(tmp_path):
    (tmp_path / "run").mkdir()
    entry, experiment = _open_experiment(tmp_path)
    first = start_activity(
        str(tmp_path),
        session_context_id=entry["session_context_id"],
        experiment_id=experiment["experiment_id"],
        objective="first started",
        activity_type="analysis",
        stage="analysis_visualization",
    )
    second = start_activity(
        str(tmp_path),
        session_context_id=entry["session_context_id"],
        experiment_id=experiment["experiment_id"],
        objective="second started",
        activity_type="analysis",
        stage="analysis_visualization",
    )
    finish_activity(
        str(tmp_path),
        session_context_id=entry["session_context_id"],
        experiment_id=experiment["experiment_id"],
        activity_id=second["activity_id"],
        status="completed",
    )
    finish_activity(
        str(tmp_path),
        session_context_id=entry["session_context_id"],
        experiment_id=experiment["experiment_id"],
        activity_id=first["activity_id"],
        status="completed",
    )

    summary = build_reentry_summary(str(tmp_path), experiment_id=experiment["experiment_id"])

    assert summary["latest_completed_activity"]["activity_id"] == first["activity_id"]


def test_reentry_recovery_checkpoint_is_experiment_scoped(tmp_path):
    (tmp_path / "run-a").mkdir()
    (tmp_path / "run-b").mkdir()
    workflow = init_workflow("custom", "computation", project_root=str(tmp_path))
    entry = project_reentry(str(tmp_path))
    experiment_a = begin_experiment(
        str(tmp_path),
        session_context_id=entry["session_context_id"],
        title="A",
        objective="A",
        stage="computation",
        root_path="run-a",
    )
    experiment_b = begin_experiment(
        str(tmp_path),
        session_context_id=entry["session_context_id"],
        title="B",
        objective="B",
        stage="computation",
        root_path="run-b",
    )
    checkpoint = create_checkpoint(
        workflow["workflow_id"],
        "computation",
        "A recovery",
        project_root=str(tmp_path),
        experiment_id=experiment_a["experiment_id"],
    )
    failure_checkpoint = create_checkpoint(
        workflow["workflow_id"],
        "computation",
        "A diagnostic failure",
        status="failure",
        project_root=str(tmp_path),
        experiment_id=experiment_a["experiment_id"],
    )

    summary_a = build_reentry_summary(str(tmp_path), experiment_id=experiment_a["experiment_id"])
    summary_b = build_reentry_summary(str(tmp_path), experiment_id=experiment_b["experiment_id"])

    assert summary_a["latest_successful_checkpoint"]["checkpoint_id"] == checkpoint["checkpoint_id"]
    assert summary_a["latest_event_checkpoint"]["checkpoint_id"] == failure_checkpoint["checkpoint_id"]
    assert summary_a["latest_event_checkpoint"]["recoverable"] is False
    assert summary_b["latest_successful_checkpoint"] is None
    assert summary_b["latest_event_checkpoint"] is None


def test_multiple_active_experiments_require_selection(tmp_path):
    for name in ("run-a", "run-b"):
        (tmp_path / name).mkdir()
    init_workflow("custom", "computation", project_root=str(tmp_path))
    entry = project_reentry(str(tmp_path))
    for name in ("run-a", "run-b"):
        begin_experiment(
            str(tmp_path),
            session_context_id=entry["session_context_id"],
            title=name,
            objective=name,
            stage="computation",
            root_path=name,
        )

    summary = build_reentry_summary(str(tmp_path))
    selected = build_reentry_summary(str(tmp_path), working_directory=str(tmp_path / "run-b"))

    assert summary["selection_required"] is True
    assert len(summary["active_experiments"]) == 2
    assert selected["selected_experiment"]["root_path"] == "run-b"


def test_handoff_closes_context(tmp_path):
    (tmp_path / "run").mkdir()
    entry, experiment = _open_experiment(tmp_path)

    handoff = session_handoff(
        str(tmp_path),
        session_context_id=entry["session_context_id"],
        experiment_id=experiment["experiment_id"],
        note="continue next session",
    )

    assert handoff["experiment_id"] == experiment["experiment_id"]
    with pytest.raises(ValueError, match="closed"):
        validate_session_context(str(tmp_path), entry["session_context_id"])


def test_failure_checkpoint_is_diagnostic_and_not_restorable(tmp_path):
    workflow = init_workflow("custom", "computation", project_root=str(tmp_path))
    checkpoint = create_checkpoint(
        workflow["workflow_id"],
        "computation",
        "diagnostic failure",
        status="failure",
        project_root=str(tmp_path),
    )

    assert checkpoint["recoverable"] is False
    with pytest.raises(ValueError, match="diagnostic-only"):
        restore_checkpoint(checkpoint["checkpoint_id"], project_root=str(tmp_path))


def test_nested_project_root_resolves_to_registered_outer_root(tmp_path):
    init_workflow("custom", "computation", project_root=str(tmp_path))
    nested = tmp_path / "phase4_computation" / "stage1_test"
    nested.mkdir(parents=True)

    with pytest.warns(UserWarning, match="canonical SimFlow root"):
        resolved = resolve_project_root(project_root=str(nested))

    assert resolved == tmp_path
