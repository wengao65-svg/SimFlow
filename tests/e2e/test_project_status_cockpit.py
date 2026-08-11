"""E2E coverage for compact project status and record filtering."""

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MCP_STATE_DIR = ROOT / "mcp" / "servers" / "simflow_state"


def _load_state_server():
    for name in [name for name in sys.modules if name == "tools" or name.startswith("tools.")]:
        del sys.modules[name]
    sys.path.insert(0, str(MCP_STATE_DIR))
    spec = importlib.util.spec_from_file_location("compact_status_cockpit", MCP_STATE_DIR / "server.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _call(server, tool, project_root, **params):
    return server.handle_request({"tool": tool, "params": {"project_root": str(project_root), **params}})


def test_project_status_tracks_current_goal_progress_and_logical_evidence(tmp_path):
    server = _load_state_server()
    review = tmp_path / "literature" / "review.md"
    proposal = tmp_path / "proposal" / "plan.md"
    model = tmp_path / "model" / "structure.cif"
    for path, content in ((review, "review\n"), (proposal, "plan\n"), (model, "structure\n")):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    literature = _call(
        server, "record", tmp_path, kind="milestone", summary="Literature baseline accepted",
        stage="literature_review", goal="compare candidate mechanisms", artifacts=["literature/review.md"],
    )["data"]
    proposal_record = _call(
        server, "record", tmp_path, kind="milestone", summary="Protocol accepted",
        stage="proposal", parent_ids=[literature["record_id"]], artifacts=["proposal/plan.md"],
    )["data"]
    run = _call(
        server, "record", tmp_path, kind="run", summary="Model validation running", status="running",
        stage="modeling", parent_ids=[proposal_record["record_id"]], artifacts=["model/structure.cif"],
        next_action="inspect validation metrics",
    )["data"]
    approval = _call(
        server, "record", tmp_path, kind="approval", summary="Production execution not approved",
        status="denied", run_id=run["run_id"], details={"run_plan_hash": "sha256:plan"},
    )["data"]

    status = _call(server, "inspect", tmp_path)
    assert status["status"] == "success"
    project = status["data"]["project"]
    assert project["current"]["goal"] == "compare candidate mechanisms"
    assert project["current"]["active_run_id"] == run["run_id"]
    assert project["current"]["latest_milestone_id"] == proposal_record["record_id"]
    assert project["current"]["next_action"] == "inspect validation metrics"
    assert project["counts"]["by_kind"] == {"approval": 1, "milestone": 2, "run": 1}
    assert status["data"]["records"][-1]["record_id"] == approval["record_id"]


def test_status_filtering_and_compact_checkpoint_readiness(tmp_path):
    server = _load_state_server()
    restart = tmp_path / "restart" / "state.bin"
    restart.parent.mkdir()
    restart.write_text("state\n", encoding="utf-8")
    first = _call(server, "record", tmp_path, kind="analysis", summary="first analysis", status="partial")["data"]
    second = _call(server, "record", tmp_path, kind="analysis", summary="accepted analysis", status="completed")["data"]
    checkpoint = _call(
        server, "checkpoint", tmp_path, summary="Analysis recovery point", record_id=second["record_id"],
        restart_refs=["restart/state.bin"], resume_command="python continue_analysis.py",
    )["data"]

    filtered = _call(server, "inspect", tmp_path, kind="analysis", status="completed")
    assert filtered["data"]["matched_count"] == 1
    assert filtered["data"]["records"][0]["record_id"] == second["record_id"]
    assert filtered["data"]["records"][0]["record_id"] != first["record_id"]
    recovered = _call(server, "recover", tmp_path, checkpoint_id=checkpoint["checkpoint_id"])
    assert recovered["data"]["ready"] is True
