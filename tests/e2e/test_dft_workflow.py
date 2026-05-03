#!/usr/bin/env python3
"""
End-to-end test: Simulate a minimal DFT workflow dry-run.

This test walks through the workflow lifecycle:
init -> literature -> review -> proposal -> modeling -> input_generation -> compute(dry-run)
"""

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "runtime"))

from lib.state import init_workflow, read_state, write_state, update_stage
from lib.artifact import register_artifact, list_artifacts
from lib.checkpoint import create_checkpoint, list_checkpoints, get_latest_checkpoint


def test_dft_workflow_dry_run():
    """Simulate a minimal DFT workflow dry-run."""
    tmpdir = tempfile.mkdtemp()
    try:
        # 1. Initialize workflow
        state = init_workflow("dft", "literature", tmpdir)
        assert state["workflow_type"] == "dft"
        assert state["current_stage"] == "literature"
        print("  [1/7] Workflow initialized")

        # 2. Literature stage
        update_stage("literature", "in_progress", tmpdir)
        register_artifact("literature_matrix.json", "literature_matrix", "literature", tmpdir)
        register_artifact("references.bib", "references", "literature", tmpdir)
        update_stage("literature", "completed", tmpdir)
        create_checkpoint(state["workflow_id"], "literature", "Literature complete", tmpdir)
        print("  [2/7] Literature stage completed")

        # 3. Review stage
        update_stage("review", "in_progress", tmpdir)
        register_artifact("review.md", "review", "review", tmpdir)
        register_artifact("gap_analysis.md", "gap_analysis", "review", tmpdir)
        update_stage("review", "completed", tmpdir)
        create_checkpoint(state["workflow_id"], "review", "Review complete", tmpdir)
        print("  [3/7] Review stage completed")

        # 4. Proposal stage
        update_stage("proposal", "in_progress", tmpdir)
        register_artifact("proposal.md", "proposal", "proposal", tmpdir)
        register_artifact("parameter_table.json", "parameter_table", "proposal", tmpdir)
        update_stage("proposal", "completed", tmpdir)
        create_checkpoint(state["workflow_id"], "proposal", "Proposal complete", tmpdir)
        print("  [4/7] Proposal stage completed")

        # 5. Modeling stage
        update_stage("modeling", "in_progress", tmpdir)
        register_artifact("POSCAR", "structure", "modeling", tmpdir)
        register_artifact("model.json", "model", "modeling", tmpdir)
        update_stage("modeling", "completed", tmpdir)
        create_checkpoint(state["workflow_id"], "modeling", "Modeling complete", tmpdir)
        print("  [5/7] Modeling stage completed")

        # 6. Input generation stage
        update_stage("input_generation", "in_progress", tmpdir)
        register_artifact("INCAR", "input_files", "input_generation", tmpdir)
        register_artifact("KPOINTS", "input_files", "input_generation", tmpdir)
        register_artifact("input_manifest.json", "input_manifest", "input_generation", tmpdir)
        update_stage("input_generation", "completed", tmpdir)
        create_checkpoint(state["workflow_id"], "input_generation", "Input gen complete", tmpdir)
        print("  [6/7] Input generation stage completed")

        # 7. Compute stage (dry-run only)
        update_stage("compute", "in_progress", tmpdir)
        register_artifact("job_script.sh", "job_script", "compute", tmpdir)
        register_artifact("dry_run_report.json", "dry_run_report", "compute", tmpdir)
        update_stage("compute", "completed", tmpdir)
        create_checkpoint(state["workflow_id"], "compute", "Compute dry-run complete", tmpdir)
        print("  [7/7] Compute stage completed (dry-run)")

        # Verify final state
        artifacts = list_artifacts(base_dir=tmpdir)
        checkpoints = list_checkpoints(tmpdir)
        latest = get_latest_checkpoint(tmpdir)

        assert len(artifacts) == 13, f"Expected 13 artifacts, got {len(artifacts)}"
        assert len(checkpoints) == 6, f"Expected 6 checkpoints, got {len(checkpoints)}"
        assert latest["stage_id"] == "compute"

        print(f"\n  Artifacts: {len(artifacts)}")
        print(f"  Checkpoints: {len(checkpoints)}")
        print(f"  Latest checkpoint: {latest['checkpoint_id']}")
        print("\n  E2E DFT workflow dry-run PASSED!")

    finally:
        shutil.rmtree(tmpdir)


if __name__ == "__main__":
    test_dft_workflow_dry_run()
