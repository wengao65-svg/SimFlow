#!/usr/bin/env python3
"""E2E coverage for the SimFlow project status cockpit."""

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MCP_STATE_DIR = ROOT / "mcp" / "servers" / "simflow_state"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(MCP_STATE_DIR))

from runtime.simflow_core.artifacts import register_artifact
from runtime.simflow_core.checkpoints import create_checkpoint
from runtime.simflow_core.gates import record_gate_decision
from runtime.simflow_core.state import init_workflow, read_state, update_stage, write_state
from runtime.simflow_core.status import build_handoff_summary, build_project_status


def _load_state_server():
    spec = importlib.util.spec_from_file_location(
        "simflow_state_server_e2e_module",
        str(MCP_STATE_DIR / "server.py"),
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write(root: Path, relative_path: str, content: str) -> None:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_project_status_cockpit_tracks_progress_evidence_and_handoff(tmp_path):
    workflow = init_workflow("custom", "literature_review", project_root=str(tmp_path))
    update_stage("literature_review", "completed", project_root=str(tmp_path))
    update_stage("proposal", "completed", project_root=str(tmp_path))
    update_stage("modeling", "in_progress", project_root=str(tmp_path))

    workflow_state = read_state(project_root=str(tmp_path), state_file="workflow.json")
    workflow_state["current_stage"] = "modeling"
    workflow_state["status"] = "in_progress"
    write_state(workflow_state, project_root=str(tmp_path), state_file="workflow.json")

    _write(tmp_path, "literature/review_summary.md", "review evidence\n")
    _write(tmp_path, "proposal/proposal.md", "proposal evidence\n")
    _write(tmp_path, "models/structure.cif", "data_structure\n")
    _write(tmp_path, "compute/dry_run_report.json", '{"status": "pass"}\n')

    review = register_artifact(
        "review_summary.md",
        "literature_review_summary",
        "literature_review",
        path="literature/review_summary.md",
        project_root=str(tmp_path),
    )
    proposal = register_artifact(
        "proposal.md",
        "proposal_document",
        "proposal",
        path="proposal/proposal.md",
        parent_artifacts=[review["artifact_id"]],
        project_root=str(tmp_path),
    )
    model = register_artifact(
        "structure.cif",
        "model_structure",
        "modeling",
        path="models/structure.cif",
        parent_artifacts=[proposal["artifact_id"]],
        project_root=str(tmp_path),
    )
    dry_run = register_artifact(
        "dry_run_report.json",
        "dry_run_report",
        "computation",
        path="compute/dry_run_report.json",
        parent_artifacts=[model["artifact_id"]],
        project_root=str(tmp_path),
    )
    checkpoint = create_checkpoint(
        workflow["workflow_id"],
        "proposal",
        "Proposal complete and modeling started",
        project_root=str(tmp_path),
    )
    decision = record_gate_decision(
        "hpc_submit",
        "rejected",
        {"reason": "approval not requested in e2e"},
        agent="e2e",
        project_root=str(tmp_path),
    )

    status = build_project_status(str(tmp_path))
    handoff = build_handoff_summary(str(tmp_path))
    server = _load_state_server()
    mcp_status = server.handle_request({"tool": "workflow_status", "params": {"project_root": str(tmp_path)}})
    mcp_graph = server.handle_request({
        "tool": "evidence_graph",
        "params": {"project_root": str(tmp_path), "artifact_id": dry_run["artifact_id"]},
    })

    assert status["workflow"]["current_stage"] == "modeling"
    assert status["progress"]["completed_stages"] == ["literature_review", "proposal"]
    assert status["next_actions"] == [
        {"action": "continue_stage", "stage": "modeling", "reason": "stage_in_progress"}
    ]
    assert status["lineage"]["node_count"] == 4
    assert status["lineage"]["link_count"] == 3
    assert status["lineage"]["missing_parents"] == []
    assert status["risks"] == []
    assert status["checkpoints"]["latest"]["checkpoint_id"] == checkpoint["checkpoint_id"]
    assert status["gates"]["latest_decisions"]["hpc_submit"]["latest_decision_id"] == decision["decision_id"]

    assert handoff["current_stage"] == "modeling"
    assert handoff["latest_checkpoint"]["stage_id"] == "proposal"
    assert mcp_status["status"] == "success"
    assert mcp_status["data"]["progress"]["completed_stages"] == ["literature_review", "proposal"]
    assert mcp_graph["status"] == "success"
    assert {node["artifact_id"] for node in mcp_graph["data"]["nodes"]} == {
        model["artifact_id"],
        dry_run["artifact_id"],
    }
