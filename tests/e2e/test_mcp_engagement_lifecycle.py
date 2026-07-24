"""End-to-end MCP state, artifact, checkpoint, verification, and handoff flow."""

import importlib.util
import sys
from pathlib import Path

from runtime.simflow_core.state import init_workflow, read_state


ROOT = Path(__file__).resolve().parents[2]


def _load_server(server_name: str):
    server_dir = ROOT / "mcp" / "servers" / server_name
    for name in [name for name in sys.modules if name == "tools" or name.startswith("tools.")]:
        del sys.modules[name]
    path_text = str(server_dir)
    if path_text in sys.path:
        sys.path.remove(path_text)
    sys.path.insert(0, path_text)
    spec = importlib.util.spec_from_file_location(f"test_{server_name}_lifecycle", server_dir / "server.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_mcp_engagement_artifact_checkpoint_verification_handoff(tmp_path):
    workflow = init_workflow("custom", "computation", project_root=str(tmp_path))
    data_dir = tmp_path / "outputs"
    data_dir.mkdir()
    (data_dir / "result.dat").write_text("1 2 3\n", encoding="utf-8")

    state_server = _load_server("simflow_state")
    status = state_server.handle_request({
        "tool": "workflow_status",
        "params": {"project_root": str(tmp_path)},
    })
    assert status["status"] == "success"

    artifact_server = _load_server("artifact_store")
    artifact_result = artifact_server.handle_request({
        "tool": "register",
        "params": {
            "project_root": str(tmp_path),
            "name": "outputs",
            "type": "output_directory",
            "stage": "computation",
            "path": "outputs",
        },
    })
    assert artifact_result["status"] == "success"
    artifact_id = artifact_result["data"]["artifact_id"]

    checkpoint_server = _load_server("checkpoint_store")
    checkpoint_result = checkpoint_server.handle_request({
        "tool": "create",
        "params": {
            "project_root": str(tmp_path),
            "workflow_id": workflow["workflow_id"],
            "stage_id": "computation",
            "description": "Computation evidence complete",
        },
    })
    assert checkpoint_result["status"] == "success"

    state_server = _load_server("simflow_state")
    completed = state_server.handle_request({
        "tool": "update_stage",
        "params": {
            "project_root": str(tmp_path),
            "stage_name": "computation",
            "status": "completed",
        },
    })
    assert completed["status"] == "success"
    handoff = state_server.handle_request({
        "tool": "session_handoff",
        "params": {"project_root": str(tmp_path)},
    })
    assert handoff["status"] == "success"

    stages = read_state(project_root=str(tmp_path), state_file="stages.json")
    verifications = read_state(project_root=str(tmp_path), state_file="verification.json")
    assert artifact_id in stages["computation"]["outputs"]
    assert stages["computation"]["checkpoint_id"] == checkpoint_result["data"]["checkpoint_id"]
    assert verifications[-1]["status"] == "pending"
    assert (tmp_path / handoff["data"]["report_path"]).is_file()
