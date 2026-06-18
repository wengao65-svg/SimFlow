#!/usr/bin/env python3
"""E2E test: AIMD workflow-layer chain without legacy runtime scripts."""

import shutil
import tempfile
from pathlib import Path

from runtime.simflow_core.artifacts import list_artifacts, register_artifact
from runtime.simflow_core.checkpoints import create_checkpoint, get_latest_checkpoint
from runtime.simflow_core.state import init_workflow, read_state, update_stage

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures"


def test_aimd_workflow_e2e():
    """Full AIMD workflow-layer E2E: state -> artifacts -> parse -> checkpoint -> handoff."""
    tmpdir = tempfile.mkdtemp()
    try:
        state = init_workflow("aimd", "modeling", tmpdir)
        workflow_id = state["workflow_id"]

        update_stage("modeling", "in_progress", tmpdir)
        register_artifact("Si.cif", "structure", "modeling", tmpdir)
        register_artifact("model.json", "model", "modeling", tmpdir)
        update_stage("modeling", "completed", tmpdir)
        create_checkpoint(workflow_id, "modeling", "Structure modeled", tmpdir)

        update_stage("computation", "in_progress", tmpdir)
        register_artifact("input_manifest.json", "input_manifest", "computation", tmpdir)
        register_artifact(
            "qe_output_Si.xml",
            "user_provided_output",
            "computation",
            tmpdir,
            metadata={
                "software": "quantum_espresso",
                "support_level": "tracked_only",
                "parser_status": "not_applicable",
                "limitation": "QE parser/validation helper support is unavailable in this SimFlow product build.",
            },
        )
        update_stage("computation", "completed", tmpdir)
        create_checkpoint(workflow_id, "computation", "AIMD computation evidence recorded", tmpdir)

        update_stage("analysis_visualization", "in_progress", tmpdir)
        register_artifact("trajectory_analysis.json", "analysis_data", "analysis_visualization", tmpdir)
        update_stage("analysis_visualization", "completed", tmpdir)

        workflow = read_state(project_root=tmpdir, state_file="workflow.json")
        stages = read_state(project_root=tmpdir, state_file="stages.json")
        artifacts = list_artifacts(project_root=tmpdir)
        latest = get_latest_checkpoint(tmpdir)

        assert workflow["workflow_type"] == "aimd"
        assert stages["modeling"]["status"] == "completed"
        assert stages["computation"]["status"] == "completed"
        assert stages["analysis_visualization"]["status"] == "completed"
        assert latest["stage_id"] == "computation"
        assert len(artifacts) == 5

    finally:
        shutil.rmtree(tmpdir)


if __name__ == "__main__":
    test_aimd_workflow_e2e()
