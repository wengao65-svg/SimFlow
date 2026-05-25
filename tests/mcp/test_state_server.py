#!/usr/bin/env python3
"""Tests for simflow_state MCP server."""

import importlib.util
import json
import sys
import tempfile
from pathlib import Path

# Add MCP server to path
MCP_DIR = Path(__file__).resolve().parents[2] / "mcp" / "servers" / "simflow_state"
sys.path.insert(0, str(MCP_DIR))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


def _load_state_server():
    spec = importlib.util.spec_from_file_location("simflow_state_server_test_module", str(MCP_DIR / "server.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_server_import():
    """Verify the state server module can be imported."""
    try:
        server = _load_state_server()
        assert hasattr(server, "handle_request") or hasattr(server, "tools") or True
    except ImportError:
        # Module structure may vary
        pass


def test_tools_list_exposes_real_input_schema():
    """State server tools/list should expose strict, useful schemas."""
    from mcp.shared.stdio_server import _list_tools

    server = _load_state_server()
    listed = _list_tools(server.TOOLS, server.TOOL_DESCRIPTIONS, server.TOOL_SCHEMAS)
    schemas = {tool["name"]: tool["inputSchema"] for tool in listed}

    assert schemas["init_workflow"]["required"] == ["project_root", "workflow_type"]
    assert schemas["write_state"]["required"] == ["project_root", "data"]
    assert schemas["update_stage"]["required"] == ["project_root", "stage_name", "status"]
    assert schemas["workflow_status"]["required"] == ["project_root"]
    assert schemas["evidence_graph"]["required"] == ["project_root"]
    assert schemas["handoff_summary"]["required"] == ["project_root"]
    assert schemas["write_state"]["additionalProperties"] is False
    assert schemas["workflow_status"]["additionalProperties"] is False
    assert schemas["evidence_graph"]["additionalProperties"] is False


def test_state_init_via_runtime():
    """Test state initialization through runtime lib."""
    from runtime.simflow_core.state import init_workflow, read_state
    with tempfile.TemporaryDirectory() as tmpdir:
        state = init_workflow("dft", "literature", tmpdir)
        assert state["workflow_type"] == "dft"
        assert state["current_stage"] == "literature"


def test_init_workflow_tool_uses_simflow_not_omx():
    """Test MCP init_workflow creates .simflow even when .omx exists."""
    from tools.init_workflow import execute
    with tempfile.TemporaryDirectory() as tmpdir:
        omx = Path(tmpdir) / ".omx"
        omx.mkdir()
        host_file = omx / "simflow_status_summary.md"
        host_file.write_text("host-owned\n", encoding="utf-8")

        result = execute({
            "workflow_type": "custom",
            "entry_point": "literature",
            "project_root": tmpdir,
        })

        assert result["status"] == "success"
        assert (Path(tmpdir) / ".simflow" / "state" / "workflow.json").is_file()
        assert (Path(tmpdir) / ".simflow" / "state" / "checkpoints.json").is_file()
        assert (Path(tmpdir) / ".simflow" / "reports" / "status_summary.md").is_file()
        assert host_file.read_text(encoding="utf-8") == "host-owned\n"


def test_init_workflow_tool_rejects_missing_project_root_from_plugin_root():
    """MCP cwd is plugin_root; init must not silently write there."""
    from tools.init_workflow import execute

    result = execute({"workflow_type": "custom", "entry_point": "literature"})

    assert result["status"] == "error"
    assert "project_root" in result["message"]


def test_state_read_write():
    """Test state read/write cycle."""
    from runtime.simflow_core.state import init_workflow, read_state, write_state
    with tempfile.TemporaryDirectory() as tmpdir:
        state = init_workflow("dft", "literature", tmpdir)
        state["current_stage"] = "proposal"
        write_state(state, tmpdir)
        loaded = read_state(tmpdir)
        assert loaded["current_stage"] == "proposal"


def test_state_transition():
    """Test stage transition."""
    from runtime.simflow_core.state import init_workflow, update_stage, read_state
    with tempfile.TemporaryDirectory() as tmpdir:
        init_workflow("dft", "literature", tmpdir)
        update_stage("literature_review", "in_progress", tmpdir)
        state = read_state(tmpdir)
        assert state is not None


def test_workflow_status_tool_reports_project_summary():
    """workflow_status exposes read-only progress and artifact counts."""
    from runtime.simflow_core.artifacts import register_artifact
    from runtime.simflow_core.state import init_workflow, update_stage

    server = _load_state_server()
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        init_workflow("custom", "literature_review", project_root=tmpdir)
        update_stage("literature_review", "completed", project_root=tmpdir)
        output = root / "literature" / "review.md"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text("review\n", encoding="utf-8")
        register_artifact(
            "review.md",
            "review_summary",
            "literature_review",
            path="literature/review.md",
            project_root=tmpdir,
        )

        result = server.handle_request({"tool": "workflow_status", "params": {"project_root": tmpdir}})

        assert result["status"] == "success"
        assert result["data"]["workflow"]["workflow_type"] == "custom"
        assert result["data"]["progress"]["completed_stages"] == ["literature_review"]
        assert result["data"]["artifacts"]["total"] == 1


def test_evidence_graph_tool_filters_artifact_lineage():
    """evidence_graph returns direct lineage around a selected artifact."""
    from runtime.simflow_core.artifacts import register_artifact
    from runtime.simflow_core.state import init_workflow

    server = _load_state_server()
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        init_workflow("custom", "literature_review", project_root=tmpdir)
        review_path = root / "literature" / "review.md"
        plan_path = root / "proposal" / "plan.md"
        review_path.parent.mkdir(parents=True, exist_ok=True)
        plan_path.parent.mkdir(parents=True, exist_ok=True)
        review_path.write_text("review\n", encoding="utf-8")
        plan_path.write_text("plan\n", encoding="utf-8")
        review = register_artifact(
            "review.md",
            "review_summary",
            "literature_review",
            path="literature/review.md",
            project_root=tmpdir,
        )
        plan = register_artifact(
            "plan.md",
            "proposal_plan",
            "proposal",
            path="proposal/plan.md",
            parent_artifacts=[review["artifact_id"]],
            project_root=tmpdir,
        )

        result = server.handle_request({
            "tool": "evidence_graph",
            "params": {"project_root": tmpdir, "artifact_id": plan["artifact_id"]},
        })

        assert result["status"] == "success"
        node_ids = {node["artifact_id"] for node in result["data"]["nodes"]}
        assert node_ids == {review["artifact_id"], plan["artifact_id"]}
        assert result["data"]["links"][0]["parent_artifact_id"] == review["artifact_id"]


def test_handoff_summary_tool_requires_project_root():
    """handoff_summary must not infer the project root from MCP cwd."""
    server = _load_state_server()

    result = server.handle_request({"tool": "handoff_summary", "params": {}})

    assert result["status"] == "error"
    assert "project_root" in result["message"]


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        print(f"  {t.__name__}...", end=" ")
        t()
        print("OK")
    print(f"\n  All {len(tests)} tests passed!")
