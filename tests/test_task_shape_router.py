"""Tests for the pure Skill schema and intent-based router contract."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _schema() -> dict:
    return json.loads((ROOT / "schemas" / "skill-contract.schema.json").read_text())


def _contract() -> dict:
    return json.loads((ROOT / "skills" / "simflow" / "router_contract.json").read_text())


def test_skill_contract_has_public_skill_types():
    schema = _schema()
    assert schema["required"] == ["skill_name", "description"]
    assert schema["properties"]["skill_type"]["enum"] == [
        "router",
        "research_task",
        "domain",
    ]


def test_skill_contract_does_not_bind_skills_to_mcp_or_approval():
    properties = _schema()["properties"]
    for removed in [
        "mcp_tools",
        "required_mcp_tools",
        "minimum_mcp_engagement",
        "requires_approval",
        "policies",
    ]:
        assert removed not in properties


def test_stage_binding_is_optional_compatibility_metadata():
    schema = _schema()
    assert "stage_binding" not in schema["required"]
    assert "current intent" in schema["properties"]["stage_binding"]["description"]
    assert "intent_binding" in schema["properties"]


def test_router_contract_has_one_task_one_domain_policy():
    policy = _contract()["selection_policy"]
    assert policy["max_research_task_skills"] == 1
    assert policy["max_domain_skills"] == 1
    assert policy["selection_basis"] == "current_user_intent"
    assert policy["directory_or_phase_drives_selection"] is False


def test_router_contract_has_no_engagement_policy():
    contract = _contract()
    assert "task_shape_engagement_policy" not in contract
    assert "state_write_triggers" not in contract
    assert "state_write_non_triggers" not in contract


def test_router_skill_has_no_mcp_lifecycle_quick_start():
    skill = (ROOT / "skills" / "simflow" / "SKILL.md").read_text(encoding="utf-8")
    for removed in [
        "Required MCP Engagement",
        "Quick Start for Re-entering a Project",
        "project_reentry",
        "begin_experiment",
        "start_activity",
        "session_handoff",
    ]:
        assert removed not in skill


def test_router_contract_host_adaptation_keeps_runtime_separate():
    policy = _contract()["host_adaptation_policy"]
    assert policy["skill_load_hooks_required"] is False
    assert policy["supported_profiles"] == ["codex", "claude_code", "opencode", "generic"]
    assert "runtime_separation" in policy["host_invariant_behavior"]
