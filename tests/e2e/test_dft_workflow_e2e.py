#!/usr/bin/env python3
"""E2E test: DFT workflow-layer chain without legacy runtime scripts."""

import shutil
import tempfile
from pathlib import Path

from runtime.lib.parsers.vasp_parser import VASPParser
from runtime.simflow_core.artifacts import list_artifacts, register_artifact
from runtime.simflow_core.checkpoints import create_checkpoint, get_latest_checkpoint
from runtime.simflow_core.state import init_workflow, read_state, update_stage

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures"


def _handoff_summary(project_root: str) -> dict:
    workflow = read_state(project_root=project_root, state_file="workflow.json")
    stages = read_state(project_root=project_root, state_file="stages.json")
    return {
        "workflow_id": workflow["workflow_id"],
        "workflow_type": workflow["workflow_type"],
        "progress": {
            "completed": [name for name, state in stages.items() if state.get("status") == "completed"],
        },
        "latest_checkpoint": get_latest_checkpoint(project_root),
    }


def test_dft_workflow_e2e():
    """Full DFT workflow-layer E2E: state -> artifacts -> parse -> checkpoint -> handoff."""
    tmpdir = tempfile.mkdtemp()
    try:
        state = init_workflow("dft", "modeling", tmpdir)
        workflow_id = state["workflow_id"]

        update_stage("modeling", "in_progress", tmpdir)
        register_artifact("POSCAR", "structure", "modeling", tmpdir)
        update_stage("modeling", "completed", tmpdir)
        create_checkpoint(workflow_id, "modeling", "Structure modeled", tmpdir)

        update_stage("computation", "in_progress", tmpdir)
        register_artifact("INCAR", "input_files", "computation", tmpdir)
        register_artifact("KPOINTS", "input_files", "computation", tmpdir)
        parsed = VASPParser().parse(str(FIXTURES_DIR / "OSZICAR_Si"))
        assert parsed.software == "vasp"
        assert parsed.final_energy is not None
        register_artifact(
            "OSZICAR_Si",
            "parsed_output",
            "computation",
            tmpdir,
            metadata={"software": parsed.software, "job_type": parsed.job_type, "final_energy": parsed.final_energy},
        )
        update_stage("computation", "completed", tmpdir)
        create_checkpoint(workflow_id, "computation", "Computation evidence parsed", tmpdir)

        handoff = _handoff_summary(tmpdir)
        artifacts = list_artifacts(project_root=tmpdir)

        assert handoff["workflow_id"] == workflow_id
        assert handoff["workflow_type"] == "dft"
        assert "modeling" in handoff["progress"]["completed"]
        assert "computation" in handoff["progress"]["completed"]
        assert handoff["latest_checkpoint"]["stage_id"] == "computation"
        assert len(artifacts) == 4

    finally:
        shutil.rmtree(tmpdir)


if __name__ == "__main__":
    test_dft_workflow_e2e()
