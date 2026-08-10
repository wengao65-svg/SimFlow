"""Cross-session tests for the forward-only experiment ledger."""

from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import json
import sqlite3
import sys

import pytest

sys.path.insert(0, str(Path(__file__).parents[2]))

from runtime.simflow_core.checkpoints import create_checkpoint, restore_checkpoint
from runtime.simflow_core.artifacts import register_artifact
from runtime.simflow_core.experiment_memory import (
    LedgerCorruptionError,
    begin_experiment,
    begin_iteration,
    build_reentry_summary,
    compare_experiments,
    evaluate_iteration,
    finish_activity,
    finish_experiment,
    fork_experiment,
    is_ledger_enabled,
    ledger_status,
    migrate_experiment_ledger,
    project_reentry,
    sanitize_for_ledger,
    session_handoff,
    start_activity,
    validate_session_context,
    verify_experiment_ledger,
)
from runtime.simflow_core.state import init_workflow, read_state, resolve_project_root


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
    (tmp_path / "run" / "restart.dat").write_text("restart\n", encoding="utf-8")
    workflow = read_state(project_root=str(tmp_path))
    recovery_checkpoint = create_checkpoint(
        workflow["workflow_id"],
        "computation",
        "round one recovery",
        project_root=str(tmp_path),
        session_context_id=entry["session_context_id"],
        experiment_id=experiment["experiment_id"],
        iteration_id=iteration["iteration_id"],
        activity_id=activity["activity_id"],
    )
    finish_activity(
        str(tmp_path),
        session_context_id=entry["session_context_id"],
        experiment_id=experiment["experiment_id"],
        activity_id=activity["activity_id"],
        status="failed",
        failure={"reason": "did not converge"},
        restart_from={"path": "run/restart.dat", "checkpoint_id": recovery_checkpoint["checkpoint_id"]},
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
        recovery={"path": "run/restart.dat", "checkpoint_id": recovery_checkpoint["checkpoint_id"]},
        next_action="adjust mixing and repeat round two",
    )

    new_entry = project_reentry(str(tmp_path), experiment_id=experiment["experiment_id"])

    assert new_entry["current_iteration"]["iteration_id"] == iteration["iteration_id"]
    assert new_entry["latest_failure"]["activity_id"] == activity["activity_id"]
    assert new_entry["latest_recovery"]["checkpoint_id"] == recovery_checkpoint["checkpoint_id"]
    assert new_entry["next_action"] == "adjust mixing and repeat round two"
    events = (tmp_path / ".simflow" / "memory" / "activity_events.jsonl").read_text(encoding="utf-8")
    assert "secret-value" not in events
    assert "[REDACTED]" in events
    assert verify_experiment_ledger(str(tmp_path))["status"] == "verified"


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
    activity = start_activity(
        str(tmp_path),
        session_context_id=entry["session_context_id"],
        experiment_id=experiment_a["experiment_id"],
        objective="Create scoped recovery checkpoints",
        activity_type="checkpoint",
        stage="computation",
    )
    checkpoint = create_checkpoint(
        workflow["workflow_id"],
        "computation",
        "A recovery",
        project_root=str(tmp_path),
        session_context_id=entry["session_context_id"],
        experiment_id=experiment_a["experiment_id"],
        activity_id=activity["activity_id"],
    )
    failure_checkpoint = create_checkpoint(
        workflow["workflow_id"],
        "computation",
        "A diagnostic failure",
        status="failure",
        project_root=str(tmp_path),
        session_context_id=entry["session_context_id"],
        experiment_id=experiment_a["experiment_id"],
        activity_id=activity["activity_id"],
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


def test_concurrent_sessions_do_not_lose_experiments(tmp_path):
    init_workflow("custom", "computation", project_root=str(tmp_path))
    first = project_reentry(str(tmp_path))
    begin_experiment(
        str(tmp_path),
        session_context_id=first["session_context_id"],
        title="seed",
        objective="enable ledger",
        stage="computation",
        root_path=".",
    )

    def create(index: int) -> str:
        entry = project_reentry(str(tmp_path))
        experiment = begin_experiment(
            str(tmp_path),
            session_context_id=entry["session_context_id"],
            title=f"parallel-{index}",
            objective="concurrency regression",
            stage="computation",
            root_path=f"run-{index}",
        )
        return experiment["experiment_id"]

    with ThreadPoolExecutor(max_workers=12) as pool:
        created = list(pool.map(create, range(24)))

    database = tmp_path / ".simflow" / "memory" / "ledger.sqlite3"
    with sqlite3.connect(database) as connection:
        count = connection.execute("SELECT COUNT(*) FROM experiments").fetchone()[0]
    exported = json.loads((tmp_path / ".simflow" / "memory" / "experiments.json").read_text(encoding="utf-8"))
    assert len(set(created)) == 24
    assert count == 25
    assert len(exported) == 25


def test_event_hash_tampering_fails_closed(tmp_path):
    entry, experiment = _open_experiment(tmp_path)
    database = tmp_path / ".simflow" / "memory" / "ledger.sqlite3"
    with sqlite3.connect(database) as connection:
        connection.execute("DROP TRIGGER events_no_update")
        connection.execute(
            "UPDATE events SET payload_json=? WHERE experiment_id=?",
            ('{"tampered":true}', experiment["experiment_id"]),
        )

    with pytest.raises(LedgerCorruptionError, match="hash verification failed"):
        ledger_status(str(tmp_path))
    with pytest.raises(LedgerCorruptionError):
        register_artifact("bad", "data", "computation", project_root=str(tmp_path))


def test_corrupt_legacy_ledger_cannot_be_silently_reset(tmp_path):
    init_workflow("custom", "computation", project_root=str(tmp_path))
    ledger = tmp_path / ".simflow" / "memory" / "ledger.json"
    ledger.write_text("{not-json\n", encoding="utf-8")

    with pytest.raises(LedgerCorruptionError, match="Cannot read"):
        project_reentry(str(tmp_path))
    assert not (tmp_path / ".simflow" / "memory" / "ledger.sqlite3").exists()


def test_structured_v1_migration_is_explicit_and_transcript_free(tmp_path):
    init_workflow("custom", "computation", project_root=str(tmp_path))
    memory = tmp_path / ".simflow" / "memory"
    context_id = "ctx_v1"
    experiment_id = "exp_v1"
    (memory / "ledger.json").write_text(json.dumps({
        "schema_version": "simflow.experiment_ledger.v1",
        "history_start": "2026-08-01T00:00:00+00:00",
    }), encoding="utf-8")
    (memory / "experiments.json").write_text(json.dumps([{
        "experiment_id": experiment_id,
        "title": "v1 experiment",
        "objective": "migrate structured records only",
        "stage": "computation",
        "root_path": ".",
        "status": "active",
    }]), encoding="utf-8")
    (memory / "iterations.json").write_text("[]\n", encoding="utf-8")
    (memory / "activity_events.jsonl").write_text("", encoding="utf-8")
    (memory / "session_contexts.jsonl").write_text(json.dumps({
        "event": "opened",
        "session_context_id": context_id,
        "working_directory": str(tmp_path),
        "ts": "2026-08-01T00:00:00+00:00",
    }) + "\n", encoding="utf-8")
    (memory / "session_handoffs.jsonl").write_text("", encoding="utf-8")

    with pytest.raises(ValueError, match="confirm=true"):
        migrate_experiment_ledger(str(tmp_path))
    result = migrate_experiment_ledger(str(tmp_path), confirm=True)

    assert result["imported"]["experiments"] == 1
    assert ledger_status(str(tmp_path))["status"] == "enabled"
    assert (memory / "v1_archive" / "ledger.json").is_file()


def test_direct_runtime_write_is_rejected_when_ledger_enabled(tmp_path):
    _open_experiment(tmp_path)

    with pytest.raises(ValueError, match="provide session_context_id"):
        register_artifact("unbound", "data", "computation", project_root=str(tmp_path))


def test_invalid_finish_references_are_rejected(tmp_path):
    entry, experiment = _open_experiment(tmp_path)
    activity = start_activity(
        str(tmp_path),
        session_context_id=entry["session_context_id"],
        experiment_id=experiment["experiment_id"],
        objective="produce result",
        activity_type="analysis",
        stage="analysis_visualization",
    )

    with pytest.raises(ValueError, match="Unknown artifact reference"):
        finish_activity(
            str(tmp_path),
            session_context_id=entry["session_context_id"],
            experiment_id=experiment["experiment_id"],
            activity_id=activity["activity_id"],
            status="completed",
            artifact_ids=["art_fake"],
        )


def test_terminal_experiment_rejects_new_activity(tmp_path):
    entry, experiment = _open_experiment(tmp_path)
    finish_experiment(
        str(tmp_path),
        session_context_id=entry["session_context_id"],
        experiment_id=experiment["experiment_id"],
        status="completed",
        conclusion="target reached",
    )

    with pytest.raises(ValueError, match="active experiment"):
        start_activity(
            str(tmp_path),
            session_context_id=entry["session_context_id"],
            experiment_id=experiment["experiment_id"],
            objective="should not start",
            activity_type="analysis",
            stage="analysis_visualization",
        )


def test_fork_and_compare_preserve_experiment_dag(tmp_path):
    entry, parent = _open_experiment(tmp_path)
    child = fork_experiment(
        str(tmp_path),
        session_context_id=entry["session_context_id"],
        parent_experiment_id=parent["experiment_id"],
        title="changed method",
        objective="compare an alternative method",
        root_path="run-child",
        hypothesis="the alternative converges faster",
    )

    comparison = compare_experiments(
        str(tmp_path), experiment_ids=[parent["experiment_id"], child["experiment_id"]]
    )
    child_summary = build_reentry_summary(str(tmp_path), experiment_id=child["experiment_id"])
    assert len(comparison["experiments"]) == 2
    assert child_summary["selected_experiment"]["parent_experiment_ids"] == [parent["experiment_id"]]


def test_pre_ledger_baseline_is_explicit_without_transcript_import(tmp_path):
    init_workflow("custom", "computation", project_root=str(tmp_path))
    baseline_file = tmp_path / "baseline.dat"
    baseline_file.write_text("baseline\n", encoding="utf-8")
    baseline = register_artifact(
        "baseline.dat",
        "data",
        "computation",
        path="baseline.dat",
        project_root=str(tmp_path),
    )
    entry = project_reentry(str(tmp_path))
    experiment = begin_experiment(
        str(tmp_path),
        session_context_id=entry["session_context_id"],
        title="forward-only continuation",
        objective="continue from declared baseline",
        stage="computation",
        root_path=".",
        baseline_refs=[{
            "kind": "artifact",
            "id": baseline["artifact_id"],
            "provenance": "pre_ledger_baseline",
        }],
    )
    summary = build_reentry_summary(str(tmp_path), experiment_id=experiment["experiment_id"])
    assert summary["ledger"]["legacy_history_imported"] is False
    assert summary["references"][0]["provenance"] == "pre_ledger_baseline"


def test_recursive_secret_redaction():
    value = {
        "command": "curl -H 'Authorization: Bearer abc123' --token=raw-secret",
        "nested": {"password": "hidden", "items": [{"api_key": "key-value"}]},
    }
    sanitized = sanitize_for_ledger(value)
    encoded = json.dumps(sanitized)
    assert "abc123" not in encoded
    assert "raw-secret" not in encoded
    assert "hidden" not in encoded
    assert "key-value" not in encoded
    compare_experiments,
    finish_experiment,
    fork_experiment,
    sanitize_for_ledger,
