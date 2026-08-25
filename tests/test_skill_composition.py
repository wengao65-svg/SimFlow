"""Tests for host-native Skill discovery and composition boundaries."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FRAMEWORK = ROOT / "skills" / "simflow" / "SKILL.md"


def test_framework_has_no_router_schema_or_numeric_selection_policy():
    text = FRAMEWORK.read_text(encoding="utf-8").lower()

    assert not (FRAMEWORK.parent / "router_contract.json").exists()
    assert "max_research_task_skills" not in text
    assert "max_domain_skills" not in text
    assert "zero or one task" not in text
    assert "zero or one domain" not in text


def test_framework_has_no_mcp_lifecycle_quick_start():
    skill = FRAMEWORK.read_text(encoding="utf-8")
    for removed in [
        "Required MCP Engagement",
        "Quick Start for Re-entering a Project",
        "project_reentry",
        "begin_experiment",
        "start_activity",
        "session_handoff",
    ]:
        assert removed not in skill


def test_documented_composition_supports_cross_responsibility_work():
    user_guide = " ".join(
        (ROOT / "docs" / "user_guide.md").read_text(encoding="utf-8").lower().split()
    )
    skill_readme = (ROOT / "skills" / "README.md").read_text(encoding="utf-8").lower()

    assert "modeling + computation" in user_guide
    assert "computation + gpumd + mlp" in user_guide
    assert "literature review + reference extraction + analysis" in user_guide
    assert "numeric cardinality limit" in skill_readme
