#!/usr/bin/env python3
"""Tests for MCP project_root routing across state, artifact, and checkpoint tools."""

import importlib.util
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _load_tool(name: str, relative_path: str):
    spec = importlib.util.spec_from_file_location(name, str(ROOT / relative_path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_artifact_store_uses_project_root_with_existing_omx():
    register = _load_tool("artifact_register_tool", "mcp/servers/artifact_store/tools/register.py")
    list_tool = _load_tool("artifact_list_tool", "mcp/servers/artifact_store/tools/list.py")
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / ".omx").mkdir()
        (root / "result.json").write_text('{"ok": true}\n', encoding="utf-8")

        result = register.execute({
            "project_root": tmpdir,
            "name": "result",
            "type": "report",
            "stage": "analysis",
            "path": "result.json",
        })
        listed = list_tool.execute({"project_root": tmpdir})

        assert result["status"] == "success"
        assert listed["status"] == "success"
        assert len(listed["data"]) == 1
        assert (root / ".simflow/state/artifacts.json").is_file()
        assert (root / ".omx").is_dir()


def test_checkpoint_store_uses_project_root_with_existing_omx():
    create = _load_tool("checkpoint_create_tool", "mcp/servers/checkpoint_store/tools/create.py")
    list_tool = _load_tool("checkpoint_list_tool", "mcp/servers/checkpoint_store/tools/list.py")
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / ".omx").mkdir()
        host_file = root / ".omx" / "session.json"
        host_file.write_text('{"owner":"host"}\n', encoding="utf-8")

        result = create.execute({
            "project_root": tmpdir,
            "workflow_id": "wf_test",
            "stage_id": "input_generation",
            "description": "checkpoint from project root",
        })
        listed = list_tool.execute({"project_root": tmpdir})

        assert result["status"] == "success"
        assert listed["status"] == "success"
        assert len(listed["data"]) == 1
        assert (root / ".simflow/state/checkpoints.json").is_file()
        assert host_file.read_text(encoding="utf-8") == '{"owner":"host"}\n'


def test_mcp_tools_reject_plugin_root_default():
    artifact_list = _load_tool("artifact_list_default_tool", "mcp/servers/artifact_store/tools/list.py")
    checkpoint_list = _load_tool("checkpoint_list_default_tool", "mcp/servers/checkpoint_store/tools/list.py")

    assert artifact_list.execute({})["status"] == "error"
    assert checkpoint_list.execute({})["status"] == "error"



def test_mcp_tools_reject_explicit_plugin_root():
    artifact_list = _load_tool("artifact_list_plugin_root_tool", "mcp/servers/artifact_store/tools/list.py")
    checkpoint_list = _load_tool("checkpoint_list_plugin_root_tool", "mcp/servers/checkpoint_store/tools/list.py")

    assert artifact_list.execute({"project_root": str(ROOT)})["status"] == "error"
    assert checkpoint_list.execute({"project_root": str(ROOT)})["status"] == "error"


def test_mcp_write_tools_reject_missing_project_root():
    init = _load_tool("state_init_missing_project_root_tool", "mcp/servers/simflow_state/tools/init_workflow.py")
    write = _load_tool("state_write_missing_project_root_tool", "mcp/servers/simflow_state/tools/write_state.py")
    update = _load_tool("state_update_missing_project_root_tool", "mcp/servers/simflow_state/tools/update_stage.py")
    register = _load_tool("artifact_register_missing_project_root_tool", "mcp/servers/artifact_store/tools/register.py")
    create = _load_tool("checkpoint_create_missing_project_root_tool", "mcp/servers/checkpoint_store/tools/create.py")
    restore = _load_tool("checkpoint_restore_missing_project_root_tool", "mcp/servers/checkpoint_store/tools/restore.py")

    calls = [
        init.execute({"workflow_type": "custom", "entry_point": "literature_review"}),
        write.execute({"data": {"workflow_id": "wf_test"}}),
        update.execute({"stage_name": "proposal", "status": "in_progress"}),
        register.execute({"name": "result", "type": "report", "stage": "analysis"}),
        create.execute({"workflow_id": "wf_test", "stage_id": "analysis"}),
        restore.execute({"checkpoint_id": "ckpt_001_analysis"}),
    ]

    for result in calls:
        assert result["status"] == "error"
        assert "project_root" in result["message"]


def test_mcp_write_tools_reject_base_dir_alias():
    init = _load_tool("state_init_base_dir_tool", "mcp/servers/simflow_state/tools/init_workflow.py")

    with tempfile.TemporaryDirectory() as tmpdir:
        result = init.execute({
            "workflow_type": "custom",
            "entry_point": "literature_review",
            "base_dir": tmpdir,
        })

        assert result["status"] == "error"
        assert "project_root" in result["message"]
        assert not (Path(tmpdir) / ".simflow").exists()


def test_mcp_write_tools_reject_explicit_plugin_root():
    init = _load_tool("state_init_plugin_root_tool", "mcp/servers/simflow_state/tools/init_workflow.py")
    write = _load_tool("state_write_plugin_root_tool", "mcp/servers/simflow_state/tools/write_state.py")
    update = _load_tool("state_update_plugin_root_tool", "mcp/servers/simflow_state/tools/update_stage.py")
    register = _load_tool("artifact_register_plugin_root_tool", "mcp/servers/artifact_store/tools/register.py")
    create = _load_tool("checkpoint_create_plugin_root_tool", "mcp/servers/checkpoint_store/tools/create.py")
    restore = _load_tool("checkpoint_restore_plugin_root_tool", "mcp/servers/checkpoint_store/tools/restore.py")

    calls = [
        init.execute({"project_root": str(ROOT), "workflow_type": "custom"}),
        write.execute({"project_root": str(ROOT), "data": {"workflow_id": "wf_test"}}),
        update.execute({"project_root": str(ROOT), "stage_name": "proposal", "status": "in_progress"}),
        register.execute({"project_root": str(ROOT), "name": "result", "type": "report", "stage": "analysis"}),
        create.execute({"project_root": str(ROOT), "workflow_id": "wf_test", "stage_id": "analysis"}),
        restore.execute({"project_root": str(ROOT), "checkpoint_id": "ckpt_001_analysis"}),
    ]

    for result in calls:
        assert result["status"] == "error"
        assert "project_root" in result["message"]
