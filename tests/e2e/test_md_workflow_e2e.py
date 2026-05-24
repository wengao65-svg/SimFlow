#!/usr/bin/env python3
"""E2E test: MD workflow-layer chain without legacy runtime scripts."""

import shutil
import tempfile
from pathlib import Path

from runtime.lib.parsers.lammps_parser import LAMMPSParser
from runtime.simflow_core.artifacts import list_artifacts, register_artifact
from runtime.simflow_core.checkpoints import create_checkpoint, get_latest_checkpoint
from runtime.simflow_core.state import init_workflow, read_state, update_stage

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures"


def _completed_stages(project_root: str) -> list[str]:
    stages = read_state(project_root=project_root, state_file="stages.json")
    return [name for name, state in stages.items() if state.get("status") == "completed"]


def test_md_workflow_e2e():
    """Full MD workflow-layer E2E: state -> artifacts -> parse -> checkpoint -> handoff."""
    tmpdir = tempfile.mkdtemp()
    try:
        state = init_workflow("md", "modeling", tmpdir)
        workflow_id = state["workflow_id"]

        update_stage("modeling", "in_progress", tmpdir)
        register_artifact("Si_4x4x4.cif", "structure", "modeling", tmpdir)
        update_stage("modeling", "completed", tmpdir)

        update_stage("computation", "in_progress", tmpdir)
        register_artifact("Si.data", "input_files", "computation", tmpdir)
        register_artifact("in.lammps", "input_files", "computation", tmpdir)
        parsed = LAMMPSParser().parse(str(FIXTURES_DIR / "lammps_log.lammps"))
        assert parsed.software == "lammps"
        assert parsed.job_type == "md"
        register_artifact(
            "lammps_log.lammps",
            "parsed_output",
            "computation",
            tmpdir,
            metadata={"software": parsed.software, "job_type": parsed.job_type, "total_steps": parsed.metadata.get("total_steps")},
        )
        update_stage("computation", "completed", tmpdir)
        create_checkpoint(workflow_id, "computation", "MD computation evidence parsed", tmpdir)

        update_stage("analysis_visualization", "in_progress", tmpdir)
        register_artifact("rdf_si.png", "figure", "analysis_visualization", tmpdir)
        register_artifact("analysis_summary.json", "analysis_data", "analysis_visualization", tmpdir)
        update_stage("analysis_visualization", "completed", tmpdir)

        artifacts = list_artifacts(project_root=tmpdir)
        completed = _completed_stages(tmpdir)
        latest = get_latest_checkpoint(tmpdir)

        assert "modeling" in completed
        assert "computation" in completed
        assert "analysis_visualization" in completed
        assert latest["stage_id"] == "computation"
        assert len(artifacts) == 6

    finally:
        shutil.rmtree(tmpdir)


if __name__ == "__main__":
    test_md_workflow_e2e()
