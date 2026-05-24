#!/usr/bin/env python3
"""End-to-end test: minimal MD workflow-layer dry-run with canonical stages."""

import shutil
import tempfile

from runtime.simflow_core.artifacts import list_artifacts, register_artifact
from runtime.simflow_core.checkpoints import create_checkpoint, get_latest_checkpoint, list_checkpoints
from runtime.simflow_core.state import init_workflow, update_stage


def test_md_workflow_dry_run():
    """Simulate a minimal MD workflow-layer dry-run."""
    tmpdir = tempfile.mkdtemp()
    try:
        state = init_workflow("md", "proposal", tmpdir)
        assert state["workflow_type"] == "md"
        assert state["current_stage"] == "proposal"

        update_stage("proposal", "in_progress", tmpdir)
        register_artifact("proposal.md", "proposal", "proposal", tmpdir)
        register_artifact("parameter_table.json", "parameter_table", "proposal", tmpdir)
        update_stage("proposal", "completed", tmpdir)
        create_checkpoint(state["workflow_id"], "proposal", "Proposal complete", tmpdir)

        update_stage("modeling", "in_progress", tmpdir)
        register_artifact("data.lammps", "lammps_data", "modeling", tmpdir)
        register_artifact("model.json", "model", "modeling", tmpdir)
        update_stage("modeling", "completed", tmpdir)
        create_checkpoint(state["workflow_id"], "modeling", "Modeling complete", tmpdir)

        update_stage("computation", "in_progress", tmpdir)
        register_artifact("in.lammps", "lammps_input", "computation", tmpdir)
        register_artifact("data.lammps", "lammps_data", "computation", tmpdir)
        register_artifact("input_manifest.json", "input_manifest", "computation", tmpdir)
        register_artifact("job_script.sh", "job_script", "computation", tmpdir)
        register_artifact("dry_run_report.json", "dry_run_report", "computation", tmpdir)
        update_stage("computation", "completed", tmpdir)
        create_checkpoint(state["workflow_id"], "computation", "Computation dry-run complete", tmpdir)

        update_stage("analysis_visualization", "in_progress", tmpdir)
        register_artifact("thermo_results.json", "thermodynamics", "analysis_visualization", tmpdir)
        register_artifact("rdf_results.json", "rdf_analysis", "analysis_visualization", tmpdir)
        register_artifact("msd_results.json", "msd_analysis", "analysis_visualization", tmpdir)
        register_artifact("diffusion_coefficient.json", "diffusion", "analysis_visualization", tmpdir)
        register_artifact("analysis_report.md", "analysis_report", "analysis_visualization", tmpdir)
        update_stage("analysis_visualization", "completed", tmpdir)
        create_checkpoint(state["workflow_id"], "analysis_visualization", "Analysis and visualization complete", tmpdir)

        update_stage("writing", "in_progress", tmpdir)
        register_artifact("manuscript_draft.md", "manuscript", "writing", tmpdir)
        register_artifact("figures.zip", "figures", "writing", tmpdir)
        update_stage("writing", "completed", tmpdir)
        create_checkpoint(state["workflow_id"], "writing", "Writing complete", tmpdir)

        artifacts = list_artifacts(project_root=tmpdir)
        checkpoints = list_checkpoints(tmpdir)
        latest = get_latest_checkpoint(tmpdir)

        assert len(artifacts) == 16
        assert len(checkpoints) == 5
        assert latest["stage_id"] == "writing"

    finally:
        shutil.rmtree(tmpdir)


if __name__ == "__main__":
    test_md_workflow_dry_run()
