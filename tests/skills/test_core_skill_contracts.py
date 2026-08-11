"""Contract tests for the open SimFlow workflow-layer skill set."""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SKILLS = ROOT / "skills"

RESEARCH_TASK_SKILLS = [
    "simflow-literature-review",
    "simflow-proposal",
    "simflow-modeling",
    "simflow-computation",
    "simflow-analysis-visualization",
    "simflow-writing",
]

ENGINE_DOMAIN_SKILLS = [
    "simflow-vasp",
    "simflow-cp2k",
    "simflow-lammps",
    "simflow-gpumd",
    "simflow-mlp",
]

UNSUPPORTED_ENGINE_PLACEHOLDERS = [
    "simflow-qe",
    "simflow-gaussian",
]

SUPPORT_SKILLS = [
    "simflow-checkpoint",
    "simflow-handoff",
    "simflow-verify",
]

PURE_TASK_REQUIRED_SECTIONS = [
    "## Purpose",
    "## Use when",
    "## Do not use when",
    "## Task principles",
    "## Minimum checks",
    "## Common failure modes",
    "## Escalate uncertainty when",
    "## Completion criteria",
    "## Optional references",
]

FORBIDDEN_TASK_RUNTIME_TERMS = [
    "project_reentry",
    "start_activity",
    "finish_activity",
    "begin_experiment",
    "session_handoff",
    "required mcp engagement",
    "update_stage",
    ".simflow/state",
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
    for skill_name in ["simflow", *RESEARCH_TASK_SKILLS, "simflow-safety-gates"]:
        skill_file = SKILLS / skill_name / "SKILL.md"
        assert skill_file.is_file(), skill_name
        text = skill_file.read_text(encoding="utf-8")
        assert f"name: {skill_name}" in text


def test_research_task_skills_are_pure_instruction_contracts():
    for skill_name in RESEARCH_TASK_SKILLS:
        text = _skill_text(skill_name).lower()
        for section in PURE_TASK_REQUIRED_SECTIONS:
            assert section.lower() in text, f"{skill_name} missing {section}"
        for term in FORBIDDEN_TASK_RUNTIME_TERMS:
            assert term not in text, f"{skill_name} contains runtime term {term}"
        assert "create a checkpoint" not in text, skill_name
        assert "register an artifact" not in text, skill_name


def test_core_skills_do_not_force_fixed_helpers_or_reports():
    for skill_name in RESEARCH_TASK_SKILLS:
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


def test_computation_preserves_scientific_execution_discipline():
    text = _skill_text("simflow-computation").lower()
    assert "scheduler submission as evidence of submission only" in text
    assert "normal process exit" in text
    assert "parser can read" in text
    assert "small diagnostic run" in text
    assert "do not silently relax scientific settings" in text
    assert "runtime safety and event recording" in text
    assert "remain separate from this guidance" in text


def test_analysis_visualization_allows_agent_written_analysis():
    text = _skill_text("simflow-analysis-visualization")
    assert "self-written Python" in text
    assert "No fixed parser or plotting library is required" in text
    assert "raw input through processing to figure data" in text


def test_analysis_visualization_reference_map_is_routable():
    text = _skill_text("simflow-analysis-visualization")
    references = [
        "plotting_principles.md",
        "simulation_output_map.md",
        "analysis_methods.md",
        "md_structure_analysis.md",
        "md_diffusion_transport.md",
        "mechanical_elastic_analysis.md",
        "electronic_structure_analysis.md",
        "phonon_vibrational_analysis.md",
        "neb_barrier_analysis.md",
        "defect_surface_adsorption_analysis.md",
        "mlp_md_analysis_readiness.md",
        "data_intake_and_profiling.md",
        "community_postprocessing_tools.md",
        "figure_contract_and_visual_qa.md",
        "tool_specific_visualization_patterns.md",
        "tooling_index.md",
    ]

    for reference in references:
        assert reference in text
        assert (SKILLS / "simflow-analysis-visualization" / "references" / reference).is_file()

def test_modeling_preserves_user_provided_models():
    text = _skill_text("simflow-modeling")
    assert "Preserve user-provided source models" in text
    assert "Builders such as ASE or pymatgen are optional tools" in text


def test_writing_requires_evidence_traceability_without_fixed_structure():
    text = _skill_text("simflow-writing")
    assert "Every substantive claim must be supportable" in text
    assert "Describe methods as executed" in text
    assert "Unsupported statements are removed, weakened, or explicitly marked" in text


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


def test_research_task_skills_match_pure_skill_validator_sections():
    for skill_name in RESEARCH_TASK_SKILLS:
        text = _skill_text(skill_name)
        for section in PURE_TASK_REQUIRED_SECTIONS:
            assert section in text, f"{skill_name} missing {section}"


def test_unsupported_engine_placeholders_do_not_claim_runtime_support():
    for skill_name in UNSUPPORTED_ENGINE_PLACEHOLDERS:
        text = _skill_text(skill_name)
        lowered = text.lower()
        assert "reserved" in lowered
        assert "does not currently provide a supported" in lowered
        assert "do not claim supported" in lowered
        assert "approval gate" in lowered
        assert "project_root" in text
        assert ".simflow" in text


def test_engine_skills_do_not_default_unknown_tasks_to_common_aliases():
    vasp_text = _skill_text("simflow-vasp")
    cp2k_text = _skill_text("simflow-cp2k")

    assert "Do not default unknown VASP tasks to `static`" in vasp_text
    assert "Do not default unknown CP2K tasks to `ENERGY`" in cp2k_text


def test_gpumd_skill_keeps_execution_and_submit_safety_boundary():
    text = _skill_text("simflow-gpumd")

    assert "helper-supported engines" in text
    assert "real execution" in text
    assert "static_input_inspection" in text
    assert "manifest_generation" in text
    assert "selected_output_parsing" in text
    assert "evidence_handoff" in text
    assert "Do not expose GPUMD/NEP real execution" in text
    assert "input generation" in text


def test_lammps_skill_covers_classic_reactive_mlp_and_reference_contracts():
    text = _skill_text("simflow-lammps")
    lowered = text.lower()
    references_dir = SKILLS / "simflow-lammps" / "references"

    for phrase in [
        "classic_md",
        "reactive_md",
        "mlp_md_deployment",
        "analysis_handoff",
        "lammps_output_intake_manifest",
        "troubleshooting",
        "simflow-mlp",
        "simflow-analysis-visualization",
        "deployment only",
    ]:
        assert phrase in lowered

    for reference in [
        "lammps_official_sources.md",
        "lammps_input_validation.md",
        "lammps_force_fields_and_mlp.md",
        "lammps_md_workflows.md",
        "lammps_output_intake.md",
        "lammps_troubleshooting.md",
    ]:
        assert reference in text
        assert (references_dir / reference).is_file()

    assert "lammps_analysis_visualization.md" not in text
    assert not (references_dir / "lammps_analysis_visualization.md").exists()
    assert "does not own final property analysis" in lowered


def test_lammps_skill_uses_consistent_english_language():
    text = _skill_text("simflow-lammps")
    assert not re.search(r"[\u4e00-\u9fff]", text)


def test_support_skills_do_not_reintroduce_fixed_executor_contracts():
    for skill_name in SUPPORT_SKILLS:
        text = _skill_text(skill_name)
        lowered = text.lower()
        assert "project_root" in text
        assert ".omx" in text
        assert "artifact" in lowered
        assert "checkpoint" in lowered
        assert "不要" in text or "do not" in lowered
        for pattern in BANNED_HARD_CONSTRAINTS:
            assert not pattern.search(text), f"{skill_name} matches {pattern.pattern}"
