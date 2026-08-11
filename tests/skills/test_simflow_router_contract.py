"""Contract tests for the thin intent-based SimFlow router."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SKILL = ROOT / "skills" / "simflow" / "SKILL.md"
CONTRACT = ROOT / "skills" / "simflow" / "router_contract.json"
CAPABILITIES = ROOT / "workflow" / "toolchains" / "capabilities.json"

TASK_SKILLS = {
    "literature_review": "simflow-literature-review",
    "proposal": "simflow-proposal",
    "modeling": "simflow-modeling",
    "computation": "simflow-computation",
    "analysis_visualization": "simflow-analysis-visualization",
    "writing": "simflow-writing",
}

DOMAIN_SKILLS = {
    "vasp": "simflow-vasp",
    "cp2k": "simflow-cp2k",
    "lammps": "simflow-lammps",
    "gpumd_nep": "simflow-gpumd",
    "mlp_methodology": "simflow-mlp",
}


def _skill_text() -> str:
    return SKILL.read_text(encoding="utf-8")


def _contract() -> dict:
    return json.loads(CONTRACT.read_text(encoding="utf-8"))


def test_router_declares_exact_public_task_and_domain_surfaces():
    contract = _contract()
    text = _skill_text()

    assert contract["research_task_skills"] == TASK_SKILLS
    assert contract["domain_skills"] == DOMAIN_SKILLS
    for skill in [*TASK_SKILLS.values(), *DOMAIN_SKILLS.values()]:
        assert skill in text


def test_router_enforces_one_task_plus_one_domain_selection():
    contract = _contract()
    policy = contract["selection_policy"]
    text = _skill_text().lower()

    assert policy["max_research_task_skills"] == 1
    assert policy["max_domain_skills"] == 1
    assert policy["selection_basis"] == "current_user_intent"
    assert policy["directory_or_phase_drives_selection"] is False
    assert "select at most one research task skill" in text
    assert "select at most one domain skill" in text


def test_router_selection_is_independent_of_directory_and_phase():
    text = _skill_text().lower()
    contract = _contract()

    assert "current intent, not cwd, directory names, workflow" in text
    assert "computation directory may need analysis guidance" in text
    assert contract["selection_policy"]["directory_or_phase_drives_selection"] is False


def test_router_separates_runtime_events_from_skill_guidance():
    text = _skill_text().lower()
    contract = _contract()

    assert "runtime is separate from skill selection" in text
    assert "does not approve, submit, transfer" in text
    assert "mandatory_mcp_engagement_from_skill_selection" in contract["prohibited_actions"]
    assert "project_reentry" not in text
    assert "start_activity" not in text
    assert "required mcp engagement" not in text


def test_router_uses_one_read_only_memory_reentry_without_session_lifecycle():
    text = _skill_text().lower()
    policy = _contract()["project_memory_policy"]

    assert policy["scope"] == "first_simflow_use_per_project_per_user_request"
    assert policy["tool"] == "inspect"
    assert policy["read_only"] is True
    assert policy["writes_session_state"] is False
    assert policy["reuse_within_request"] is True
    assert policy["silent_binding_requires_unambiguous_match"] is True
    assert "read-only `inspect` tool once" in text
    assert "do not create session state" in text
    assert "do not repeat `inspect`" in text
    assert "fixed recovery summary" in text


def test_router_escalates_high_risk_events_to_runtime_without_support_skill():
    text = _skill_text().lower()
    triggers = set(_contract()["runtime_escalation_triggers"])

    for phrase in [
        "real local or remote execution",
        "scheduler",
        "credentials",
        "licensed or proprietary files",
        "potcar",
        "destructive actions",
        "state recovery",
    ]:
        assert phrase in text
    assert "simflow-safety-gates" not in text
    assert "simflow-checkpoint" not in text
    assert "simflow-handoff" not in text
    assert "real_local_execution" in triggers
    assert "vasp_potcar_material" in triggers


def test_ambiguous_intent_does_not_default_to_known_paths():
    text = _skill_text().lower()
    policy = _contract()["ambiguous_intent_policy"]

    assert policy["return_smallest_plausible_skill_set"] is True
    assert policy["do_not_default_unknown_software_to_supported_helper"] is True
    assert policy["do_not_default_unknown_computation_tasks_to_known_tasks"] == [
        "static",
        "ENERGY",
        "NVT",
        "training",
    ]
    assert "do not default unknown software" in text
    assert "do not default an unknown computation" in text


def test_router_defers_capability_detail_to_shared_contract():
    contract = _contract()
    capabilities = json.loads(CAPABILITIES.read_text(encoding="utf-8"))
    reference = contract["toolchain_contract_reference"]

    assert {"gpumd", "nep"} <= set(capabilities["helper_supported_software"])
    assert reference["source"] == "workflow/toolchains/capabilities.json"
    assert "Single source of truth" in reference["purpose"]
    assert "shared toolchain" in _skill_text().lower()


def test_router_prohibits_execution_and_fabrication():
    text = _skill_text().lower()
    prohibited = set(_contract()["prohibited_actions"])

    assert "centralized workflow executor" in text
    assert "fabricate literature" in text
    assert "centralized_executor_behavior" in prohibited
    assert "fabricated_literature_results_data_figures_citations_convergence_or_job_states" in prohibited
