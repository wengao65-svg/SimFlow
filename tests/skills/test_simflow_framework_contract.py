"""Contract tests for the opt-in SimFlow Framework Skill."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SKILL = ROOT / "skills" / "simflow" / "SKILL.md"
OPENAI_METADATA = ROOT / "skills" / "simflow" / "agents" / "openai.yaml"


def _skill_text() -> str:
    return SKILL.read_text(encoding="utf-8")


def _normalized_skill_text() -> str:
    return " ".join(_skill_text().lower().split())


def test_framework_is_explicit_only_on_codex_and_claude():
    skill = _skill_text()
    metadata = OPENAI_METADATA.read_text(encoding="utf-8")

    assert "disable-model-invocation: true" in skill
    assert "allow_implicit_invocation: false" in metadata
    assert "Use $simflow" in metadata


def test_framework_does_not_restore_a_central_router_contract():
    text = _skill_text().lower()

    assert not (SKILL.parent / "router_contract.json").exists()
    assert "host agent owns discovery and composition" in text
    assert "does not maintain an intent map" in text
    assert "do not route or select research task, domain, or custom skills" in text
    assert "do not impose skill cardinality limits" in text


def test_framework_allows_multi_skill_and_host_native_composition():
    text = _normalized_skill_text()

    assert "multiple research task or domain skills may be combined" in text
    assert "host-native custom skills may participate" in text
    assert "not a numeric cardinality rule" in text


def test_project_memory_reentry_is_conditional_and_read_only():
    text = _normalized_skill_text()

    assert "only when the current request depends on existing simflow" in text
    assert "call read-only `inspect` once" in text
    assert "do not inspect merely because a simflow skill is active" in text
    assert "do not create session or activity state" in text
    assert "unambiguous experiment match silently" in text


def test_framework_keeps_runtime_and_scientific_truth_boundaries():
    text = _normalized_skill_text()

    assert "ordinary reading, reasoning, editing, analysis, plotting, and" in text
    assert "do not require a state write" in text
    assert "without approval bound to the current immutable run plan" in text
    assert "scheduler job id as submitted, not completed" in text
    assert "never fabricate literature, data, figures, convergence" in text
    assert "licensed potcar content" in text
