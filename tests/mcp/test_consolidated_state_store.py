"""Compact state-store integration tests."""

from runtime.simflow_core.records import (
    create_recovery_checkpoint,
    inspect_project,
    record_event,
    recover_checkpoint,
)


def test_project_summary_tracks_current_run_milestone_and_failure(tmp_path):
    run = record_event(
        str(tmp_path),
        kind="run",
        summary="production run submitted",
        status="submitted",
    )
    milestone = record_event(
        str(tmp_path),
        kind="milestone",
        summary="baseline accepted",
        next_action="compare variants",
    )
    failure = record_event(
        str(tmp_path),
        kind="failure",
        summary="variant diverged",
        run_id=run["run_id"],
        status="failed",
    )

    state = inspect_project(str(tmp_path))
    current = state["project"]["current"]
    assert current["active_run_id"] == run["run_id"]
    assert current["latest_milestone_id"] == milestone["record_id"]
    assert current["latest_failure_id"] == failure["record_id"]
    assert current["next_action"] == "compare variants"
    assert state["project"]["counts"]["total"] == 3


def test_terminal_run_clears_only_matching_active_run(tmp_path):
    first = record_event(str(tmp_path), kind="run", summary="first", status="running")
    second = record_event(str(tmp_path), kind="run", summary="second", status="running")
    record_event(
        str(tmp_path), kind="run", summary="first done", status="completed", run_id=first["run_id"]
    )
    assert inspect_project(str(tmp_path))["project"]["current"]["active_run_id"] == second["run_id"]
    record_event(
        str(tmp_path), kind="run", summary="second done", status="completed", run_id=second["run_id"]
    )
    assert inspect_project(str(tmp_path))["project"]["current"]["active_run_id"] is None


def test_latest_checkpoint_can_be_recovered_without_explicit_id(tmp_path):
    input_path = tmp_path / "input.inp"
    input_path.write_text("input\n", encoding="utf-8")
    checkpoint = create_recovery_checkpoint(
        str(tmp_path),
        summary="ready to resume",
        input_refs=["input.inp"],
        resume_command="solver input.inp",
    )

    result = recover_checkpoint(str(tmp_path))
    assert result["checkpoint"]["checkpoint_id"] == checkpoint["checkpoint_id"]
    assert result["ready"] is True


def test_checkpoint_requires_real_recovery_reference(tmp_path):
    try:
        create_recovery_checkpoint(str(tmp_path), summary="empty")
    except ValueError as error:
        assert "recovery reference" in str(error)
    else:
        raise AssertionError("checkpoint without recovery references should fail")
