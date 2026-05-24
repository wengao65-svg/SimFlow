#!/usr/bin/env python3
"""End-to-end test: minimal DFT workflow-layer dry-run with canonical stages."""

import shutil
import tempfile

from runtime.simflow_core.artifacts import list_artifacts, register_artifact
from runtime.simflow_core.checkpoints import create_checkpoint, get_latest_checkpoint, list_checkpoints
from runtime.simflow_core.state import init_workflow, update_stage


def test_dft_workflow_dry_run():
    """Simulate a minimal DFT workflow-layer dry-run."""
    tmpdir = tempfile.mkdtemp()
    try:
        state = init_workflow("dft", "literature_review", tmpdir)
        assert state["workflow_type"] == "dft"
        assert state["current_stage"] == "literature_review"

        update_stage("literature_review", "in_progress", tmpdir)
        register_artifact("literature_matrix.json", "literature_matrix", "literature_review", tmpdir)
        register_artifact("references.bib", "references", "literature_review", tmpdir)
        update_stage("literature_review", "completed", tmpdir)
        create_checkpoint(state["workflow_id"], "literature_review", "Literature review complete", tmpdir)

        update_stage("proposal", "in_progress", tmpdir)
        register_artifact("proposal.md", "proposal", "proposal", tmpdir)
        register_artifact("parameter_table.json", "parameter_table", "proposal", tmpdir)
        update_stage("proposal", "completed", tmpdir)
        create_checkpoint(state["workflow_id"], "proposal", "Proposal complete", tmpdir)

        update_stage("modeling", "in_progress", tmpdir)
        register_artifact("POSCAR", "structure", "modeling", tmpdir)
        register_artifact("model.json", "model", "modeling", tmpdir)
        update_stage("modeling", "completed", tmpdir)
        create_checkpoint(state["workflow_id"], "modeling", "Modeling complete", tmpdir)

        update_stage("computation", "in_progress", tmpdir)
        register_artifact("INCAR", "input_files", "computation", tmpdir)
        register_artifact("KPOINTS", "input_files", "computation", tmpdir)
        register_artifact("input_manifest.json", "input_manifest", "computation", tmpdir)
        register_artifact("job_script.sh", "job_script", "computation", tmpdir)
        register_artifact("dry_run_report.json", "dry_run_report", "computation", tmpdir)
        update_stage("computation", "completed", tmpdir)
        create_checkpoint(state["workflow_id"], "computation", "Computation dry-run complete", tmpdir)

        artifacts = list_artifacts(project_root=tmpdir)
        checkpoints = list_checkpoints(tmpdir)
        latest = get_latest_checkpoint(tmpdir)

        assert len(artifacts) == 11
        assert len(checkpoints) == 4
        assert latest["stage_id"] == "computation"

    finally:
        shutil.rmtree(tmpdir)


if __name__ == "__main__":
    test_dft_workflow_dry_run()
