"""Static checks for SimFlow scaffold templates."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_skill_scaffold_generates_frontmatter_and_pure_guidance_sections():
    text = (ROOT / "scripts" / "scaffold_skill.js").read_text(encoding="utf-8")

    assert "const template = `---" in text
    assert "name: ${skillName}" in text
    assert "description: ${description" in text
    assert "显式 project_root" in text
    assert "Skill 本身不要求状态写入" in text
    assert "绑定审批" in text
    assert "唯一合法路径" in text


def test_stage_scaffold_uses_open_stage_schema_fields():
    text = (ROOT / "scripts" / "scaffold_stage.js").read_text(encoding="utf-8")

    for field in [
        "intent",
        "acceptable_inputs",
        "evidence_outputs",
        "recommended_skills",
        "suggested_checks",
        "approval_triggers",
        "handoff_notes",
        "risk_notes",
    ]:
        assert field in text

    for legacy_field in [
        "default_agent",
        "default_skill",
        "required_inputs",
        "expected_outputs",
        "validators",
        "approval_gates",
        "recovery_policy",
    ]:
        assert legacy_field not in text
