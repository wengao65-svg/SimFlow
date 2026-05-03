#!/usr/bin/env python3
"""
End-to-end test: Simulate a minimal MD workflow dry-run.

This test walks through the workflow lifecycle:
init -> proposal -> modeling -> input_generation -> compute(dry-run) -> analysis -> writing

MD workflow uses LAMMPS as the primary engine.
"""

import json
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "runtime"))

from lib.state import init_workflow, read_state, write_state, update_stage
from lib.artifact import register_artifact, list_artifacts
from lib.checkpoint import create_checkpoint, list_checkpoints, get_latest_checkpoint


def test_md_workflow_dry_run():
    """Simulate a minimal MD workflow dry-run."""
    tmpdir = tempfile.mkdtemp()
    try:
        # 1. Initialize workflow
        state = init_workflow("md", "proposal", tmpdir)
        assert state["workflow_type"] == "md"
        assert state["current_stage"] == "proposal"
        print("  [1/7] MD workflow initialized")

        # 2. Proposal stage
        update_stage("proposal", "in_progress", tmpdir)
        register_artifact("proposal.md", "proposal", "proposal", tmpdir)
        register_artifact("parameter_table.json", "parameter_table", "proposal", tmpdir)
        update_stage("proposal", "completed", tmpdir)
        create_checkpoint(state["workflow_id"], "proposal", "Proposal complete", tmpdir)
        print("  [2/7] Proposal stage completed")

        # 3. Modeling stage
        update_stage("modeling", "in_progress", tmpdir)
        register_artifact("data.lammps", "lammps_data", "modeling", tmpdir)
        register_artifact("model.json", "model", "modeling", tmpdir)
        update_stage("modeling", "completed", tmpdir)
        create_checkpoint(state["workflow_id"], "modeling", "Modeling complete", tmpdir)
        print("  [3/7] Modeling stage completed")

        # 4. Input generation stage (MD uses LAMMPS inputs)
        update_stage("input_generation", "in_progress", tmpdir)
        register_artifact("in.lammps", "lammps_input", "input_generation", tmpdir)
        register_artifact("data.lammps", "lammps_data", "input_generation", tmpdir)
        register_artifact("input_manifest.json", "input_manifest", "input_generation", tmpdir)
        update_stage("input_generation", "completed", tmpdir)
        create_checkpoint(state["workflow_id"], "input_generation", "Input gen complete", tmpdir)
        print("  [4/7] Input generation stage completed")

        # 5. Compute stage (dry-run)
        update_stage("compute", "in_progress", tmpdir)
        register_artifact("job_script.sh", "job_script", "compute", tmpdir)
        register_artifact("dry_run_report.json", "dry_run_report", "compute", tmpdir)
        update_stage("compute", "completed", tmpdir)
        create_checkpoint(state["workflow_id"], "compute", "Compute dry-run complete", tmpdir)
        print("  [5/7] Compute stage completed (dry-run)")

        # 6. Analysis stage (MD: thermodynamics, RDF, MSD)
        update_stage("analysis", "in_progress", tmpdir)
        register_artifact("thermo_results.json", "thermodynamics", "analysis", tmpdir)
        register_artifact("rdf_results.json", "rdf_analysis", "analysis", tmpdir)
        register_artifact("msd_results.json", "msd_analysis", "analysis", tmpdir)
        register_artifact("diffusion_coefficient.json", "diffusion", "analysis", tmpdir)
        register_artifact("analysis_report.md", "analysis_report", "analysis", tmpdir)
        update_stage("analysis", "completed", tmpdir)
        create_checkpoint(state["workflow_id"], "analysis", "Analysis complete", tmpdir)
        print("  [6/7] Analysis stage completed")

        # 7. Writing stage
        update_stage("writing", "in_progress", tmpdir)
        register_artifact("manuscript_draft.md", "manuscript", "writing", tmpdir)
        register_artifact("figures.zip", "figures", "writing", tmpdir)
        update_stage("writing", "completed", tmpdir)
        create_checkpoint(state["workflow_id"], "writing", "Writing complete", tmpdir)
        print("  [7/7] Writing stage completed")

        # Verify final state
        artifacts = list_artifacts(base_dir=tmpdir)
        checkpoints = list_checkpoints(tmpdir)
        latest = get_latest_checkpoint(tmpdir)

        assert len(artifacts) == 16, "Expected 16 artifacts, got {}".format(len(artifacts))
        assert len(checkpoints) == 6, "Expected 6 checkpoints, got {}".format(len(checkpoints))
        assert latest["stage_id"] == "writing"

        print("\n  Artifacts: {}".format(len(artifacts)))
        print("  Checkpoints: {}".format(len(checkpoints)))
        print("  Latest checkpoint: {}".format(latest["checkpoint_id"]))
        print("\n  E2E MD workflow dry-run PASSED!")

    finally:
        shutil.rmtree(tmpdir)


if __name__ == "__main__":
    test_md_workflow_dry_run()
