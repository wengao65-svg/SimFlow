#!/usr/bin/env python3
"""E2E test: checkpoint recovery with canonical workflow stages."""

import shutil
import tempfile

from runtime.simflow_core.artifacts import list_artifacts, register_artifact
from runtime.simflow_core.checkpoints import create_checkpoint, list_checkpoints, restore_checkpoint
from runtime.simflow_core.state import init_workflow, read_state, update_stage, write_state


def test_checkpoint_recovery():
    """Test checkpoint creation, simulated failure, and recovery."""
    tmpdir = tempfile.mkdtemp()
    try:
        state = init_workflow("dft", "modeling", tmpdir)
        workflow_id = state["workflow_id"]
        assert state["current_stage"] == "modeling"

        update_stage("modeling", "in_progress", tmpdir)
        register_artifact("POSCAR", "structure", "modeling", tmpdir)
        register_artifact("model.json", "model", "modeling", tmpdir)
        update_stage("modeling", "completed", tmpdir, inputs=["seed"], outputs=["POSCAR", "model.json"])
        ckpt1 = create_checkpoint(workflow_id, "modeling", "Modeling complete", tmpdir)
        assert ckpt1 is not None

        update_stage("computation", "in_progress", tmpdir)
        register_artifact("INCAR", "input_files", "computation", tmpdir)
        register_artifact("KPOINTS", "input_files", "computation", tmpdir)
        register_artifact("dry_run_report.json", "dry_run_report", "computation", tmpdir)
        update_stage(
            "computation",
            "completed",
            tmpdir,
            inputs=["POSCAR", "model.json"],
            outputs=["INCAR", "KPOINTS", "dry_run_report.json"],
        )
        ckpt2 = create_checkpoint(workflow_id, "computation", "Computation dry-run complete", tmpdir)
        assert ckpt2 is not None

        update_stage("analysis_visualization", "in_progress", tmpdir)
        register_artifact("analysis_report.json", "analysis_report", "analysis_visualization", tmpdir)
        workflow = read_state(tmpdir, "workflow.json")
        workflow["status"] = "corrupted"
        write_state(workflow, tmpdir)
        assert read_state(tmpdir, "workflow.json")["status"] == "corrupted"

        result = restore_checkpoint(ckpt2["checkpoint_id"], tmpdir)
        assert result is not None
        restored = read_state(tmpdir, "workflow.json")
        restored_stages = read_state(tmpdir, "stages.json")
        assert restored["workflow_id"] == workflow_id
        assert restored["workflow_type"] == "dft"
        assert restored_stages["computation"]["status"] == "completed"
        assert restored_stages["computation"]["inputs"] == ["POSCAR", "model.json"]
        assert restored_stages["computation"]["outputs"] == ["INCAR", "KPOINTS", "dry_run_report.json"]
        assert restored_stages["computation"]["checkpoint_id"] == ckpt2["checkpoint_id"]

        update_stage("analysis_visualization", "in_progress", tmpdir)
        register_artifact("energy.dat", "data", "analysis_visualization", tmpdir)
        update_stage("analysis_visualization", "completed", tmpdir)
        create_checkpoint(workflow_id, "analysis_visualization", "Analysis complete after recovery", tmpdir)

        artifacts = list_artifacts(project_root=tmpdir)
        checkpoints = list_checkpoints(tmpdir)
        completed = read_state(tmpdir, "stages.json")

        assert len(checkpoints) >= 3
        assert len(artifacts) >= 6
        assert completed["analysis_visualization"]["status"] == "completed"

        restore_checkpoint(ckpt1["checkpoint_id"], tmpdir)
        active_registry = read_state(tmpdir, "checkpoints.json")
        listed_after_restore = list_checkpoints(tmpdir)

        assert [entry["checkpoint_id"] for entry in active_registry] == [ckpt1["checkpoint_id"]]
        assert [entry["checkpoint_id"] for entry in listed_after_restore] == [ckpt1["checkpoint_id"]]

    finally:
        shutil.rmtree(tmpdir)


if __name__ == "__main__":
    test_checkpoint_recovery()
