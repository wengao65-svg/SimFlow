"""Contract tests for the open SimFlow workflow-layer skill set."""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SKILLS = ROOT / "skills"

CORE_SKILLS = [
    "simflow",
    "simflow-literature-review",
    "simflow-proposal",
    "simflow-modeling",
    "simflow-computation",
    "simflow-analysis-visualization",
    "simflow-writing",
    "simflow-safety-gates",
]

ENGINE_DOMAIN_SKILLS = [
    "simflow-vasp",
    "simflow-cp2k",
    "simflow-qe",
    "simflow-lammps",
    "simflow-gaussian",
]

BANNED_HARD_CONSTRAINTS = [
    re.compile(r"must\s+use\s+parse_[\w.-]+\.py", re.IGNORECASE),
    re.compile(r"must\s+generate\s+(methods|results|final_handoff)\.md", re.IGNORECASE),
    re.compile(r"必须使用\s*`?parse_[^`\s]+\.py`?"),
    re.compile(r"必须生成\s*`?(methods|results|final_handoff)\.md`?"),
    re.compile(r"must\s+use\s+(VASP|QE|Quantum ESPRESSO|CP2K|LAMMPS|Gaussian)\b", re.IGNORECASE),
    re.compile(r"必须使用\s*(VASP|QE|Quantum ESPRESSO|CP2K|LAMMPS|Gaussian)"),
]


def _skill_text(skill_name: str) -> str:
    return (SKILLS / skill_name / "SKILL.md").read_text(encoding="utf-8")


def test_canonical_core_skills_exist():
    for skill_name in CORE_SKILLS:
        skill_file = SKILLS / skill_name / "SKILL.md"
        assert skill_file.is_file(), skill_name
        text = skill_file.read_text(encoding="utf-8")
        assert f"name: {skill_name}" in text


def test_core_skills_keep_state_artifact_checkpoint_contracts():
    for skill_name in CORE_SKILLS:
        text = _skill_text(skill_name).lower()
        assert "artifact" in text, skill_name
        assert "checkpoint" in text, skill_name
        assert "project_root" in text or ".simflow" in text, skill_name


def test_core_skills_do_not_force_fixed_helpers_or_reports():
    for skill_name in CORE_SKILLS:
        text = _skill_text(skill_name)
        for pattern in BANNED_HARD_CONSTRAINTS:
            assert not pattern.search(text), f"{skill_name} matches {pattern.pattern}"


def test_legacy_executor_skill_entries_are_removed():
    removed = [
        "simflow-literature",
        "simflow-compute",
        "simflow-analysis",
        "simflow-visualization",
        "simflow-pipeline",
        "simflow-stage",
        "simflow-input-generation",
        "simflow-review",
        "simflow-plan",
        "simflow-intake",
        "simflow-ralph",
        "simflow-team",
    ]
    for skill_name in removed:
        assert not (SKILLS / skill_name / "SKILL.md").exists(), skill_name


def test_computation_requires_approval_without_fixed_software():
    text = _skill_text("simflow-computation").lower()
    assert "approval" in text
    assert "dry-run" in text
    assert "credential" in text
    assert "do not require one specific simulation engine" in text


def test_analysis_visualization_allows_agent_written_analysis():
    text = _skill_text("simflow-analysis-visualization")
    assert "self-written Python" in text
    assert "Do not require a fixed parser" in text
    assert "Figure lineage" in text


def test_modeling_preserves_user_provided_models():
    text = _skill_text("simflow-modeling")
    assert "用户提供的原始模型必须保留" in text
    assert "不要强制使用内置 crystal builder" in text


def test_writing_requires_evidence_traceability_without_fixed_structure():
    text = _skill_text("simflow-writing")
    assert "关键科学 claim 必须链接" in text
    assert "不要求固定文档结构" in text
    assert "不要强制生成某个固定报告文件" in text


def test_engine_skills_are_domain_assistants_not_workflow_executors():
    for skill_name in ENGINE_DOMAIN_SKILLS:
        text = _skill_text(skill_name)
        lowered = text.lower()
        assert "domain assistant" in lowered or "domain assistance" in lowered or "domain assistant" in text
        assert "not a central workflow executor" in lowered or "not the workflow contract" in lowered or "不决定顶层 workflow" in text
        assert "helper-run manifest" in lowered
        assert "approval gate" in lowered
        assert "only valid" in lowered or "唯一合法" in text
        assert "unknown" in lowered or "未知" in text


def test_engine_skills_do_not_default_unknown_tasks_to_common_aliases():
    vasp_text = _skill_text("simflow-vasp")
    cp2k_text = _skill_text("simflow-cp2k")
    qe_text = _skill_text("simflow-qe")

    assert "Do not default unknown VASP tasks to `static`" in vasp_text
    assert "Do not default unknown CP2K tasks to `ENERGY`" in cp2k_text
    assert "不要默认未知 QE 任务为 SCF" in qe_text
