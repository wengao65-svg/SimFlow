"""E2E compact checkpoint validation without state rollback."""

from runtime.simflow_core.checkpoints import create_checkpoint, restore_checkpoint
from runtime.simflow_core.state import init_workflow, read_state, write_state


def test_checkpoint_recovery(tmp_path):
    workflow = init_workflow("dft", "computation", project_root=str(tmp_path))
    restart = tmp_path / "calc" / "restart.wfn"
    restart.parent.mkdir()
    restart.write_text("restart\n", encoding="utf-8")
    checkpoint = create_checkpoint(
        workflow["workflow_id"], "computation", "resume computation",
        project_root=str(tmp_path), restart_refs=["calc/restart.wfn"],
        resume_command="solver --restart calc/restart.wfn",
    )

    state = read_state(project_root=str(tmp_path), state_file="workflow.json")
    state["status"] = "failed_after_checkpoint"
    write_state(state, project_root=str(tmp_path), state_file="workflow.json")
    recovery = restore_checkpoint(checkpoint["checkpoint_id"], project_root=str(tmp_path))

    assert recovery["recovery_validation"]["ready"] is True
    assert recovery["state_restored"] is False
    assert read_state(project_root=str(tmp_path), state_file="workflow.json")["status"] == "failed_after_checkpoint"
