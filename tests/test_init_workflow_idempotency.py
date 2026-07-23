#!/usr/bin/env python3
"""Tests for init_workflow idempotency and force backup.

Covers P0.1: ensuring init_workflow does NOT clobber existing .simflow/state
files (especially gates.json, jobs.json) when called on an already-initialized
project. Also verifies force=True backs up the tree before recreating state.
"""

import json
import sys
import tempfile
from pathlib import Path

# Ensure runtime is importable
ROOT = Path(__file__).resolve().parents[1]  # tests/ -> simflow/
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "runtime"))

# Ensure the simflow_state MCP server tools are importable
MCP_STATE_DIR = ROOT / "mcp" / "servers" / "simflow_state"
sys.path.insert(0, str(MCP_STATE_DIR))


def _init_workflow(*args, **kwargs):
    from runtime.simflow_core.state import init_workflow
    return init_workflow(*args, **kwargs)


def _read_state(project_root, state_file="workflow.json"):
    from runtime.simflow_core.state import read_state
    return read_state(project_root=project_root, state_file=state_file)


def _import_init_workflow_tool():
    from tools.init_workflow import execute
    return execute


def test_first_init_creates_all_canonical_files():
    """First init on empty project creates all 11 state files + reports/status_summary.md."""
    with tempfile.TemporaryDirectory() as tmpdir:
        state = _init_workflow("custom", "computation", project_root=tmpdir)
        assert state["workflow_type"] == "custom"
        assert state["current_stage"] == "computation"
        assert state["status"] == "initialized"

        simflow_state = Path(tmpdir) / ".simflow" / "state"
        for filename in [
            "workflow.json", "project.json", "summary.json", "stages.json",
            "artifacts.json", "checkpoints.json", "gates.json", "jobs.json",
            "lineage.json", "verification.json", "metadata.json",
        ]:
            assert (simflow_state / filename).is_file(), f"missing {filename}"

        assert (Path(tmpdir) / ".simflow" / "reports" / "status_summary.md").is_file()


def test_second_init_preserves_existing_state():
    """Second init on already-initialized project must NOT overwrite any state file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        first = _init_workflow("custom", "computation", project_root=tmpdir)
        workflow_id_first = first["workflow_id"]
        created_at_first = first["created_at"]

        # Mutate some state files to simulate real work
        from runtime.simflow_core.state import write_state
        custom_gates = [{"gate_id": "gate_001_test", "decision": "approved"}]
        write_state(custom_gates, project_root=tmpdir, state_file="gates.json")
        custom_jobs = [{"job_id": "job_test_1", "status": "completed"}]
        write_state(custom_jobs, project_root=tmpdir, state_file="jobs.json")
        custom_artifacts = [{"artifact_id": "art_test_1"}]
        write_state(custom_artifacts, project_root=tmpdir, state_file="artifacts.json")

        # Second init with different workflow_type/entry_point — must be no-op
        second = _init_workflow("different_type", "literature_review", project_root=tmpdir)

        # Workflow identity preserved
        assert second["workflow_id"] == workflow_id_first, "workflow_id changed!"
        assert second["workflow_type"] == "custom", "workflow_type changed!"
        assert second["current_stage"] == "computation", "current_stage changed!"
        assert second["created_at"] == created_at_first, "created_at changed!"

        # Custom state files preserved
        gates = _read_state(tmpdir, "gates.json")
        assert gates == custom_gates, "gates.json was clobbered!"
        jobs = _read_state(tmpdir, "jobs.json")
        assert jobs == custom_jobs, "jobs.json was clobbered!"
        artifacts = _read_state(tmpdir, "artifacts.json")
        assert artifacts == custom_artifacts, "artifacts.json was clobbered!"


def test_force_init_backs_up_and_recreates():
    """force=True backs up existing .simflow tree and recreates canonical state."""
    with tempfile.TemporaryDirectory() as tmpdir:
        first = _init_workflow("custom", "computation", project_root=tmpdir)
        original_workflow_id = first["workflow_id"]

        # Add real custom state
        from runtime.simflow_core.state import write_state
        custom_gates = [{"gate_id": "gate_001_test", "decision": "approved"}]
        write_state(custom_gates, project_root=tmpdir, state_file="gates.json")

        # Force re-init
        result = _init_workflow("new_type", "literature_review", project_root=tmpdir, force=True)

        # workflow_id is preserved (same research project identity)
        assert result["workflow_id"] == original_workflow_id
        assert result["workflow_type"] == "new_type"
        assert result["current_stage"] == "literature_review"

        # Backup was created
        backup_root = Path(tmpdir) / ".simflow" / "backups"
        assert backup_root.is_dir()
        backups = list(backup_root.iterdir())
        assert len(backups) == 1, f"expected 1 backup, got {len(backups)}"
        backup_path = backups[0]

        # Backup contains the OLD gates.json with custom data
        backed_up_gates_path = backup_path / "state" / "gates.json"
        assert backed_up_gates_path.is_file()
        backed_up_gates = json.loads(backed_up_gates_path.read_text(encoding="utf-8"))
        assert backed_up_gates == custom_gates

        # Current gates.json is reset to canonical empty []
        current_gates = _read_state(tmpdir, "gates.json")
        assert current_gates == [], "force did not reset gates.json"


def test_force_init_preserves_created_at_when_existing():
    """force=True preserves original created_at (only updated_at moves forward)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        first = _init_workflow("custom", "computation", project_root=tmpdir)
        original_created_at = first["created_at"]

        result = _init_workflow("new_type", "literature_review", project_root=tmpdir, force=True)
        assert result["created_at"] == original_created_at
        assert result["updated_at"] != original_created_at


def test_mcp_init_workflow_tool_defaults_to_idempotent():
    """MCP tool execute() must default to non-destructive path."""
    execute = _import_init_workflow_tool()

    with tempfile.TemporaryDirectory() as tmpdir:
        first = execute({
            "workflow_type": "custom",
            "entry_point": "computation",
            "project_root": tmpdir,
        })
        assert first["status"] == "success"
        original_workflow_id = first["data"]["workflow_id"]

        # Add custom gates.json
        from runtime.simflow_core.state import write_state
        write_state(
            [{"gate_id": "gate_user_custom"}],
            project_root=tmpdir,
            state_file="gates.json",
        )

        # Second call without force — must preserve custom gates
        second = execute({
            "workflow_type": "different_type",
            "entry_point": "literature_review",
            "project_root": tmpdir,
        })
        assert second["status"] == "success"
        assert second["data"]["workflow_id"] == original_workflow_id
        assert "backup_path" not in second

        gates = _read_state(tmpdir, "gates.json")
        assert gates == [{"gate_id": "gate_user_custom"}], "MCP default path clobbered gates.json"


def test_mcp_init_workflow_tool_force_returns_backup_path():
    """MCP tool with force=True returns backup_path field."""
    execute = _import_init_workflow_tool()

    with tempfile.TemporaryDirectory() as tmpdir:
        execute({
            "workflow_type": "custom",
            "entry_point": "computation",
            "project_root": tmpdir,
        })

        result = execute({
            "workflow_type": "new_type",
            "entry_point": "literature_review",
            "project_root": tmpdir,
            "force": True,
        })
        assert result["status"] == "success"
        assert "backup_path" in result
        assert Path(result["backup_path"]).is_dir()


def test_init_workflow_on_empty_project_does_not_create_backup():
    """First init (no existing state) must not create a backup directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        _init_workflow("custom", "computation", project_root=tmpdir, force=True)
        backup_root = Path(tmpdir) / ".simflow" / "backups"
        # Backup dir may exist as empty (mkdir in _backup path); must have no entries
        if backup_root.exists():
            assert not any(backup_root.iterdir()), "unexpected backup on first init"


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
