"""Tests for the pure Skill schema and intent-based router contract."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _contract() -> dict:
    return json.loads((ROOT / "skills" / "simflow" / "router_contract.json").read_text())


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
    assert "single_read_only_memory_reentry" in policy["host_invariant_behavior"]
    assert _contract()["project_memory_policy"]["writes_session_state"] is False
