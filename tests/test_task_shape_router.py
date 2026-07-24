#!/usr/bin/env python3
"""Tests for P3.4 + P7.1 + P7.2: task-shape-aware router + skill-contract schema.

P7.1: skill-contract.schema.json has required_mcp_tools, minimum_mcp_engagement,
      and task_shapes fields
P7.2: router_contract.json has task_shape_engagement_policy with all task shapes
P3.4: router SKILL.md has Required MCP Engagement + Quick Start sections
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def test_skill_contract_schema_has_required_mcp_tools():
    """skill-contract.schema.json includes required_mcp_tools field."""
    schema = json.loads((ROOT / "schemas" / "skill-contract.schema.json").read_text())
    assert "required_mcp_tools" in schema["properties"]
    assert schema["properties"]["required_mcp_tools"]["type"] == "array"
    assert "default" in schema["properties"]["required_mcp_tools"]


def test_skill_contract_schema_has_minimum_mcp_engagement():
    """skill-contract.schema.json includes minimum_mcp_engagement field."""
    schema = json.loads((ROOT / "schemas" / "skill-contract.schema.json").read_text())
    assert "minimum_mcp_engagement" in schema["properties"]
    assert schema["properties"]["minimum_mcp_engagement"]["type"] == "integer"
    assert schema["properties"]["minimum_mcp_engagement"]["default"] == 1


def test_skill_contract_schema_has_task_shapes():
    """skill-contract.schema.json includes task_shapes field."""
    schema = json.loads((ROOT / "schemas" / "skill-contract.schema.json").read_text())
    assert "task_shapes" in schema["properties"]
    assert schema["properties"]["task_shapes"]["type"] == "array"


def test_router_contract_has_task_shape_engagement_policy():
    """router_contract.json includes task_shape_engagement_policy."""
    contract = json.loads(
        (ROOT / "skills" / "simflow" / "router_contract.json").read_text()
    )
    assert "task_shape_engagement_policy" in contract
    policy = contract["task_shape_engagement_policy"]
    assert policy["all_task_shapes_require_engagement"] is True
    assert policy["engagement_floor"] == "simflow_state/read_state"


def test_router_contract_has_single_stage_compute_pattern():
    """router_contract.json includes single_stage_compute task shape pattern."""
    contract = json.loads(
        (ROOT / "skills" / "simflow" / "router_contract.json").read_text()
    )
    patterns = contract["task_shape_engagement_policy"]["task_shape_patterns"]
    assert "single_stage_compute" in patterns
    assert patterns["single_stage_compute"]["minimum_engagement"] == 1


def test_router_contract_has_multi_stage_research_pattern():
    """router_contract.json includes multi_stage_research task shape pattern."""
    contract = json.loads(
        (ROOT / "skills" / "simflow" / "router_contract.json").read_text()
    )
    patterns = contract["task_shape_engagement_policy"]["task_shape_patterns"]
    assert "multi_stage_research" in patterns
    assert patterns["multi_stage_research"]["minimum_engagement"] >= 2


def test_router_skill_has_required_mcp_engagement_section():
    """simflow/SKILL.md includes Required MCP Engagement section."""
    skill = (ROOT / "skills" / "simflow" / "SKILL.md").read_text(encoding="utf-8")
    assert "## Required MCP Engagement" in skill
    assert "read_state" in skill
    assert "task-shape" in skill.lower() or "Task-shape" in skill


def test_router_skill_has_quick_start_section():
    """simflow/SKILL.md includes Quick Start for Re-entering a Project section."""
    skill = (ROOT / "skills" / "simflow" / "SKILL.md").read_text(encoding="utf-8")
    assert "## Quick Start for Re-entering a Project" in skill
    assert "read_state" in skill
    assert "init_workflow" in skill
    assert "session_handoff" in skill
    assert "orphan_compute_scanner" in skill


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
