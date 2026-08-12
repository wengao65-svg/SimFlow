from __future__ import annotations

import json

import pytest

from runtime.simflow_core.experiment_notebook import (
    ExperimentNotebookError,
    NotebookFormatError,
    append_experiment_entry,
    create_experiment,
    parse_experiment_notebook,
)
from runtime.simflow_core.project_summary import (
    build_project_summary,
    project_summary_is_stale,
    rebuild_project_summary,
)
from runtime.simflow_core.records import record_event


def _create(tmp_path):
    return create_experiment(
        str(tmp_path),
        title="NEPv3 high-temperature dataset",
        research_question="Should structures at or above 400 K enter NEPv3?",
        scope_paths=["stage6_NEP/NEPv3"],
        tags=["nep", "dataset"],
        idempotency_key="create-nepv3-temperature-scope",
    )


def test_create_and_parse_append_only_notebook(tmp_path):
    created = _create(tmp_path)
    parsed = parse_experiment_notebook(created["path"])

    assert parsed["header"]["experiment_id"] == created["experiment_id"]
    assert parsed["entries"][0]["details"]["scope_paths"] == ["stage6_NEP/NEPv3"]
    assert "Should structures at or above 400 K" in created["path"].read_text(encoding="utf-8")


def test_experiment_creation_is_idempotent_for_same_id_and_key(tmp_path):
    created = create_experiment(
        str(tmp_path),
        experiment_id="exp_123456789abc",
        title="Question",
        research_question="What changes?",
        scope_paths=["."],
        idempotency_key="same",
    )
    repeated = create_experiment(
        str(tmp_path),
        experiment_id="exp_123456789abc",
        title="Ignored rendering",
        research_question="Ignored",
        scope_paths=["."],
        idempotency_key="same",
    )

    assert repeated["idempotent_replay"] is True
    assert repeated["entry"]["entry_id"] == created["entry"]["entry_id"]


def test_notebook_ontology_is_limited_to_four_entry_types(tmp_path):
    experiment_id = _create(tmp_path)["experiment_id"]
    for entry_type in ("material_action", "recovery", "validation", "failure"):
        with pytest.raises(ExperimentNotebookError, match="Unsupported experiment entry_type"):
            append_experiment_entry(
                str(tmp_path),
                experiment_id=experiment_id,
                entry_type=entry_type,
                summary="Not part of the scientific-memory ontology",
            )


def test_attempts_are_explicit_and_references_must_resolve(tmp_path):
    experiment_id = _create(tmp_path)["experiment_id"]
    with pytest.raises(ExperimentNotebookError, match="Unknown attempt_id"):
        append_experiment_entry(
            str(tmp_path),
            experiment_id=experiment_id,
            entry_type="observation",
            attempt_id="att_missing",
            summary="This reference must not be accepted",
        )

    attempt = append_experiment_entry(
        str(tmp_path),
        experiment_id=experiment_id,
        entry_type="attempt",
        attempt_id="att_expanded_training",
        summary="Train NEPv3 with the expanded high-temperature dataset",
    )["entry"]
    observation = append_experiment_entry(
        str(tmp_path),
        experiment_id=experiment_id,
        entry_type="observation",
        attempt_id=attempt["attempt_id"],
        summary="Validation remains stable at 800 K",
    )["entry"]

    assert observation["attempt_id"] == "att_expanded_training"


def test_append_is_idempotent_and_redacts_restricted_content(tmp_path):
    experiment_id = _create(tmp_path)["experiment_id"]
    first = append_experiment_entry(
        str(tmp_path),
        experiment_id=experiment_id,
        entry_type="decision",
        summary="Accept filtered dataset",
        details={"password": "hidden", "potcar_content": "restricted"},
        idempotency_key="accept-filtered-dataset",
    )
    second = append_experiment_entry(
        str(tmp_path),
        experiment_id=experiment_id,
        entry_type="decision",
        summary="duplicate",
        idempotency_key="accept-filtered-dataset",
    )

    assert second["idempotent_replay"] is True
    assert first["entry"]["entry_id"] == second["entry"]["entry_id"]
    text = first["path"].read_text(encoding="utf-8")
    assert "hidden" not in text
    assert "restricted" not in text


def test_malformed_notebook_fails_closed(tmp_path):
    path = _create(tmp_path)["path"]
    path.write_text(path.read_text(encoding="utf-8").replace('"schema_version":"simflow.experiment_entry.v1"', '"schema_version":'), encoding="utf-8")

    with pytest.raises(NotebookFormatError):
        parse_experiment_notebook(path)


def test_notebook_with_action_field_fails_closed(tmp_path):
    path = _create(tmp_path)["path"]
    text = path.read_text(encoding="utf-8")
    path.write_text(text.replace('"entry_type":"experiment"', '"action":"create","entry_type":"experiment"'), encoding="utf-8")

    with pytest.raises(NotebookFormatError, match="do not support action"):
        parse_experiment_notebook(path)


def test_project_summary_rebuilds_from_notebooks_records_and_checkpoints(tmp_path):
    experiment_id = _create(tmp_path)["experiment_id"]
    append_experiment_entry(
        str(tmp_path),
        experiment_id=experiment_id,
        entry_type="observation",
        summary="The retained dataset contains 196 frames",
        next_action="train NEPv3",
    )
    record_event(
        str(tmp_path),
        kind="run",
        summary="submitted training",
        status="submitted",
        run_id="slurm_123",
        details={"experiment_id": experiment_id, "attempt_id": "att_training"},
    )
    checkpoint_dir = tmp_path / ".simflow" / "checkpoints"
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    (checkpoint_dir / "ckpt_manual.json").write_text(json.dumps({"checkpoint_id": "ckpt_manual"}), encoding="utf-8")

    summary = rebuild_project_summary(str(tmp_path))
    assert summary["counts"]["experiments"] == 1
    assert summary["counts"]["operational_total"] == 1
    assert summary["counts"]["checkpoints"] == 1
    assert summary["current"]["active_run_ids"] == ["slurm_123"]
    assert summary["current"]["next_action"] == "train NEPv3"
    assert project_summary_is_stale(str(tmp_path)) is False

    (tmp_path / ".simflow" / "project.json").unlink()
    rebuilt = rebuild_project_summary(str(tmp_path), write=False)
    assert rebuilt["experiments"][0]["research_question"].startswith("Should structures")
    assert not (tmp_path / ".simflow" / "project.json").exists()


def test_summary_detects_stale_cache_after_new_entry(tmp_path):
    experiment_id = _create(tmp_path)["experiment_id"]
    rebuild_project_summary(str(tmp_path))
    assert project_summary_is_stale(str(tmp_path)) is False

    append_experiment_entry(
        str(tmp_path),
        experiment_id=experiment_id,
        entry_type="decision",
        summary="Run another diagnostic attempt",
    )
    assert project_summary_is_stale(str(tmp_path)) is True
