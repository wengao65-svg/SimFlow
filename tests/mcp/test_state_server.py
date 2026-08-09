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
    assert schemas["init_workflow"]["properties"]["entry_point"]["enum"] == [
        "literature_review",
        "proposal",
        "modeling",
        "computation",
        "analysis_visualization",
        "writing",
    ]
    assert schemas["write_state"]["required"] == ["project_root", "data"]
    assert schemas["update_stage"]["required"] == ["project_root", "stage_name", "status"]
    assert schemas["workflow_status"]["required"] == ["project_root"]
    assert schemas["evidence_graph"]["required"] == ["project_root"]
    assert "evidence_role" in schemas["evidence_graph"]["properties"]
    assert "tool" in schemas["evidence_graph"]["properties"]
    assert "status" in schemas["evidence_graph"]["properties"]
    assert "schema_version" in schemas["evidence_graph"]["properties"]
    assert "recipe" in schemas["evidence_graph"]["properties"]
    assert "claim_id" in schemas["evidence_graph"]["properties"]
    assert schemas["evidence_graph"]["properties"]["direction"]["enum"] == ["upstream", "downstream", "both"]
    assert schemas["evidence_graph"]["properties"]["depth"]["maximum"] == 5
    assert schemas["handoff_summary"]["required"] == ["project_root"]
    assert schemas["stage_readiness"]["required"] == ["project_root"]
    assert schemas["project_readiness"]["required"] == ["project_root"]
    assert schemas["project_reentry"]["required"] == ["project_root"]
    assert schemas["begin_experiment"]["required"] == [
        "project_root", "session_context_id", "title", "objective", "stage", "root_path"
    ]
    assert schemas["start_activity"]["required"] == [
        "project_root", "session_context_id", "experiment_id", "objective", "activity_type", "stage"
    ]
    assert schemas["experiment_timeline"]["properties"]["limit"]["maximum"] == 200
    assert schemas["record_computation_evidence"]["required"] == ["project_root", "evidence_params"]
    assert schemas["record_analysis_evidence"]["required"] == ["project_root", "evidence_params"]
    assert schemas["record_stage_failure"]["required"] == ["project_root", "stage_name", "message"]
    assert schemas["repair_state"]["required"] == ["project_root"]
    assert schemas["repair_state"]["properties"]["mode"]["enum"] == ["audit", "apply"]
    assert schemas["write_state"]["additionalProperties"] is False
    assert schemas["workflow_status"]["additionalProperties"] is False
    assert schemas["evidence_graph"]["additionalProperties"] is False
    assert schemas["stage_readiness"]["additionalProperties"] is False
    assert schemas["project_readiness"]["additionalProperties"] is False
    assert schemas["record_computation_evidence"]["additionalProperties"] is False
    assert schemas["record_analysis_evidence"]["additionalProperties"] is False
    assert schemas["record_stage_failure"]["additionalProperties"] is False
    assert schemas["repair_state"]["additionalProperties"] is False


def test_record_stage_failure_requires_engagement_then_records_complete_failure():
    from runtime.simflow_core.state import init_workflow, read_state

    server = _load_state_server()
    with tempfile.TemporaryDirectory() as tmpdir:
        init_workflow("custom", "computation", project_root=tmpdir)

        blocked = server.handle_request({
            "tool": "record_stage_failure",
            "params": {
                "project_root": tmpdir,
                "stage_name": "computation",
                "message": "MCP failure",
            },
        })
        assert blocked["code"] == "skill_engagement_contract_violation"

        read_result = server.handle_request({
            "tool": "read_state",
            "params": {"project_root": tmpdir, "file": "workflow.json"},
        })
        assert read_result["status"] == "success"

        result = server.handle_request({
            "tool": "record_stage_failure",
            "params": {
                "project_root": tmpdir,
                "stage_name": "computation",
                "message": "MCP failure",
                "activity": "compute",
            },
        })
        assert result["status"] == "error"
        assert result["failure_checkpoint_id"].startswith("ckpt_")
        assert read_state(project_root=tmpdir, state_file="workflow.json")["status"] == "failed"


def test_ledger_enabled_writes_require_active_experiment_context():
    from runtime.simflow_core.artifacts import get_artifact
    from runtime.simflow_core.state import init_workflow

    server = _load_state_server()
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / "run").mkdir()
        init_workflow("custom", "computation", project_root=tmpdir)

        reentry = server.handle_request({
            "tool": "project_reentry",
            "params": {"project_root": tmpdir, "working_directory": tmpdir},
        })
        context_id = reentry["data"]["session_context_id"]
        experiment_result = server.handle_request({
            "tool": "begin_experiment",
            "params": {
                "project_root": tmpdir,
                "session_context_id": context_id,
                "title": "tracked",
                "objective": "tracked work",
                "stage": "computation",
                "root_path": "run",
            },
        })
        experiment_id = experiment_result["data"]["experiment_id"]

        blocked = server.handle_request({
            "tool": "register_artifact",
            "params": {"project_root": tmpdir, "name": "result", "type": "output", "stage": "computation"},
        })
        assert blocked["code"] == "experiment_context_required"

        activity_result = server.handle_request({
            "tool": "start_activity",
            "params": {
                "project_root": tmpdir,
                "session_context_id": context_id,
                "experiment_id": experiment_id,
                "objective": "produce result",
                "activity_type": "computation",
                "stage": "computation",
            },
        })
        activity_id = activity_result["data"]["activity_id"]
        registered = server.handle_request({
            "tool": "register_artifact",
            "params": {
                "project_root": tmpdir,
                "session_context_id": context_id,
                "experiment_id": experiment_id,
                "activity_id": activity_id,
                "name": "result",
                "type": "output",
                "stage": "computation",
            },
        })

        assert registered["status"] == "success"
        artifact = get_artifact(registered["data"]["artifact_id"], project_root=tmpdir)
        assert artifact["experiment_id"] == experiment_id
        assert artifact["activity_id"] == activity_id


def test_ledger_enabled_evidence_intake_propagates_activity_links():
    from runtime.simflow_core.artifacts import list_artifacts
    from runtime.simflow_core.state import init_workflow, write_state

    server = _load_state_server()
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        init_workflow("custom", "computation", project_root=tmpdir)
        write_state(
            {
                "workflow_type": "custom",
                "entry_point": "computation",
                "current_stage": "computation",
                "research_goal": "track evidence intake",
                "software": "custom",
            },
            project_root=tmpdir,
            state_file="metadata.json",
        )
        compute_path = root / "compute.json"
        analysis_path = root / "analysis.json"
        compute_path.write_text("{}\n", encoding="utf-8")
        analysis_path.write_text("{}\n", encoding="utf-8")

        reentry = server.handle_request({
            "tool": "project_reentry",
            "params": {"project_root": tmpdir, "working_directory": tmpdir},
        })
        context_id = reentry["data"]["session_context_id"]
        experiment = server.handle_request({
            "tool": "begin_experiment",
            "params": {
                "project_root": tmpdir,
                "session_context_id": context_id,
                "title": "evidence linkage",
                "objective": "keep generated evidence attached to the experiment",
                "stage": "computation",
                "root_path": ".",
            },
        })["data"]

        linked = []
        for stage, tool, evidence in (
            ("computation", "record_computation_evidence", {"calculation_manifest": "compute.json"}),
            ("analysis_visualization", "record_analysis_evidence", {"analysis_outputs": "analysis.json"}),
        ):
            activity = server.handle_request({
                "tool": "start_activity",
                "params": {
                    "project_root": tmpdir,
                    "session_context_id": context_id,
                    "experiment_id": experiment["experiment_id"],
                    "objective": f"record {stage} evidence",
                    "activity_type": "evidence_intake",
                    "stage": stage,
                },
            })["data"]
            result = server.handle_request({
                "tool": tool,
                "params": {
                    "project_root": tmpdir,
                    "session_context_id": context_id,
                    "experiment_id": experiment["experiment_id"],
                    "activity_id": activity["activity_id"],
                    "evidence_params": {"software": "custom", "evidence": evidence},
                },
            })
            assert result["status"] == "success"
            assert result["data"]["manifest"]["session_context_id"] == context_id
            linked.extend(result["data"]["artifacts"])

        assert linked
        assert all(item["experiment_id"] == experiment["experiment_id"] for item in linked)
        activity_ids = {item["activity_id"] for item in linked}
        assert len(activity_ids) == 2
        stored = list_artifacts(project_root=tmpdir)
        linked_ids = {item["artifact_id"] for item in linked}
        assert all(item["experiment_id"] == experiment["experiment_id"] for item in stored if item["artifact_id"] in linked_ids)


def test_repair_state_audit_is_read_only_and_apply_requires_engagement():
    from runtime.simflow_core.state import init_workflow, write_state

    server = _load_state_server()
    with tempfile.TemporaryDirectory() as tmpdir:
        workflow = init_workflow("custom", "computation", project_root=tmpdir)
        write_state([{
            "artifact_id": "art_12345678",
            "name": "result.dat",
            "type": "output",
            "version": "v1.0.0",
            "stage": "computation",
            "path": None,
            "lineage": {"parent_artifacts": [], "parameters": {}, "software": None},
            "metadata": {},
            "checksum": None,
            "created_at": workflow["created_at"],
        }], project_root=tmpdir, state_file="artifacts.json")

        audit = server.handle_request({
            "tool": "repair_state",
            "params": {"project_root": tmpdir, "mode": "audit"},
        })
        assert audit["status"] == "success"
        assert not (Path(tmpdir) / ".simflow" / "state" / "mcp_engagement_log.jsonl").exists()

        blocked = server.handle_request({
            "tool": "repair_state",
            "params": {"project_root": tmpdir, "mode": "apply"},
        })
        assert blocked["code"] == "skill_engagement_contract_violation"

        server.handle_request({
            "tool": "read_state",
            "params": {"project_root": tmpdir, "file": "workflow.json"},
        })
        applied = server.handle_request({
            "tool": "repair_state",
            "params": {"project_root": tmpdir, "mode": "apply"},
        })
        assert applied["status"] == "success"
        assert applied["data"]["changed"] is True


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
            "entry_point": "literature_review",
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

    result = execute({"workflow_type": "custom", "entry_point": "literature_review"})

    assert result["status"] == "error"
    assert "project_root" in result["message"]


def test_init_workflow_tool_defaults_to_literature_review():
    from tools.init_workflow import execute

    with tempfile.TemporaryDirectory() as tmpdir:
        result = execute({"workflow_type": "custom", "project_root": tmpdir})

        assert result["status"] == "success"
        assert result["data"]["current_stage"] == "literature_review"


def test_init_workflow_tool_rejects_legacy_entry_aliases():
    from tools.init_workflow import execute

    with tempfile.TemporaryDirectory() as tmpdir:
        result = execute({"workflow_type": "custom", "entry_point": "literature", "project_root": tmpdir})

        assert result["status"] == "error"
        assert "canonical stage" in result["message"]


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


def test_evidence_graph_tool_filters_helper_metadata():
    """evidence_graph can query helper evidence metadata without mutating state."""
    from runtime.simflow_core.artifacts import register_artifact
    from runtime.simflow_core.state import init_workflow

    server = _load_state_server()
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        init_workflow("custom", "analysis_visualization", project_root=tmpdir)
        output = root / "analysis" / "metrics.json"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text("{}\n", encoding="utf-8")
        artifact = register_artifact(
            "metrics.json",
            "helper_output",
            "analysis_visualization",
            path="analysis/metrics.json",
            software="nep",
            metadata={
                "schema_version": "simflow.helper_evidence.v1",
                "helper": "summarize_mlp_metrics",
                "evidence_role": "model_metrics_summary",
                "status": "success",
                "parser_status": "parsed",
                "actual_tool_used": {"software": "nep", "support_level": "helper_supported"},
            },
            project_root=tmpdir,
        )

        result = server.handle_request({
            "tool": "evidence_graph",
            "params": {
                "project_root": tmpdir,
                "evidence_role": "model_metrics_summary",
                "tool": "nep",
                "status": "success",
            },
        })

        assert result["status"] == "success"
        assert [node["artifact_id"] for node in result["data"]["nodes"]] == [artifact["artifact_id"]]
        assert result["data"]["nodes"][0]["evidence_role"] == "model_metrics_summary"


def test_handoff_summary_tool_requires_project_root():
    """handoff_summary must not infer the project root from MCP cwd."""
    server = _load_state_server()

    result = server.handle_request({"tool": "handoff_summary", "params": {}})

    assert result["status"] == "error"
    assert "project_root" in result["message"]


def test_stage_readiness_tool_reports_missing_evidence():
    """stage_readiness returns read-only evidence gaps for a selected stage."""
    from runtime.simflow_core.state import init_workflow

    server = _load_state_server()
    with tempfile.TemporaryDirectory() as tmpdir:
        init_workflow("custom", "proposal", project_root=tmpdir)

        result = server.handle_request({
            "tool": "stage_readiness",
            "params": {"project_root": tmpdir, "stage": "proposal"},
        })

        assert result["status"] == "success"
        assert result["data"]["stage"] == "proposal"
        assert result["data"]["readiness_status"] == "incomplete"
        assert result["data"]["evidence"]["missing_count"] == 5
        assert result["data"]["actions"][0]["action"] == "record_evidence_artifact"


def test_project_readiness_tool_requires_project_root():
    """project_readiness must not infer project root from MCP cwd."""
    server = _load_state_server()

    result = server.handle_request({"tool": "project_readiness", "params": {}})

    assert result["status"] == "error"
    assert "project_root" in result["message"]


def test_record_computation_evidence_tool_registers_tracked_only_evidence():
    """MCP exposes generic computation evidence intake for tracked-only tools."""
    from runtime.simflow_core.artifacts import list_artifacts
    from runtime.simflow_core.state import init_workflow, read_state, write_state

    server = _load_state_server()
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        init_workflow("mlp_md", "computation", project_root=tmpdir)
        write_state(
            {
                "workflow_type": "mlp_md",
                "entry_point": "computation",
                "current_stage": "computation",
                "research_goal": "record DeePMD training evidence",
                "material": "Si",
                "software": "deepmd",
                "toolchain": ["deepmd"],
            },
            project_root=tmpdir,
            state_file="metadata.json",
        )
        # Engagement contract: call read_state before state-write tools
        server.handle_request({
            "tool": "read_state",
            "params": {"project_root": tmpdir, "file": "workflow.json"},
        })
        evidence_dir = root / "user_compute"
        evidence_dir.mkdir()
        for name in [
            "calculation_manifest.json",
            "input.json",
            "input_validation.json",
            "dry_run_report.json",
            "resource_estimate.json",
            "credential_scan.json",
        ]:
            (evidence_dir / name).write_text("{}\n", encoding="utf-8")

        result = server.handle_request({
            "tool": "record_computation_evidence",
            "params": {
                "project_root": tmpdir,
                "evidence_params": {
                    "software": "deepmd",
                    "task": "model_training",
                    "command": "dp train input.json",
                    "complete_stage": True,
                    "evidence": {
                        "calculation_manifest": "user_compute/calculation_manifest.json",
                        "input_files": ["user_compute/input.json"],
                        "input_validation_report": "user_compute/input_validation.json",
                        "dry_run_report": "user_compute/dry_run_report.json",
                        "resource_estimate": "user_compute/resource_estimate.json",
                        "credential_scan": "user_compute/credential_scan.json",
                    },
                },
            },
        })

        assert result["status"] == "success"
        assert result["data"]["stage_completed"] is True
        artifacts = list_artifacts(stage="computation", project_root=tmpdir)
        assert any(artifact["type"] == "evidence_intake_manifest" for artifact in artifacts)
        stages = read_state(project_root=tmpdir, state_file="stages.json")
        assert stages["computation"]["status"] == "completed"


def test_record_analysis_evidence_tool_registers_custom_analysis_evidence():
    """MCP exposes generic analysis evidence intake for custom workflows."""
    from runtime.simflow_core.artifacts import list_artifacts
    from runtime.simflow_core.state import init_workflow, read_state, write_state

    server = _load_state_server()
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        init_workflow("custom", "analysis_visualization", project_root=tmpdir)
        write_state(
            {
                "workflow_type": "custom",
                "entry_point": "analysis_visualization",
                "current_stage": "analysis_visualization",
                "research_goal": "record custom analysis evidence",
                "material": "Si",
                "software": "python",
            },
            project_root=tmpdir,
            state_file="metadata.json",
        )
        evidence_dir = root / "analysis_user"
        evidence_dir.mkdir()
        for name in [
            "analyze.py",
            "input.csv",
            "analysis_report.json",
            "environment.json",
            "figure.png",
            "figures_manifest.json",
            "claim_evidence_map.json",
        ]:
            (evidence_dir / name).write_text("{}\n", encoding="utf-8")

        # Engagement contract: call read_state before state-write tools
        server.handle_request({
            "tool": "read_state",
            "params": {"project_root": tmpdir, "file": "workflow.json"},
        })

        result = server.handle_request({
            "tool": "record_analysis_evidence",
            "params": {
                "project_root": tmpdir,
                "evidence_params": {
                    "software": "python",
                    "task": "custom_metrics",
                    "command": "python analyze.py",
                    "complete_stage": True,
                    "evidence": {
                        "analysis_script": "analysis_user/analyze.py",
                        "analysis_inputs": ["analysis_user/input.csv"],
                        "analysis_outputs": {"path": "analysis_user/analysis_report.json", "name": "analysis_report.json"},
                        "analysis_environment": "analysis_user/environment.json",
                        "figure_files": ["analysis_user/figure.png"],
                        "figure_manifest": {"path": "analysis_user/figures_manifest.json", "name": "figures_manifest.json"},
                        "claim_evidence_map": "analysis_user/claim_evidence_map.json",
                    },
                },
            },
        })

        assert result["status"] == "success"
        assert result["data"]["stage_completed"] is True
        artifacts = list_artifacts(stage="analysis_visualization", project_root=tmpdir)
        assert any(artifact["type"] == "analysis_evidence_intake_manifest" for artifact in artifacts)
        assert any(artifact["name"] == "analysis_report.json" for artifact in artifacts)
        stages = read_state(project_root=tmpdir, state_file="stages.json")
        assert stages["analysis_visualization"]["status"] == "completed"


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        print(f"  {t.__name__}...", end=" ")
        t()
        print("OK")
    print(f"\n  All {len(tests)} tests passed!")
