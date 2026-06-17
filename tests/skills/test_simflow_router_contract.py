"""Contract tests for the top-level SimFlow router skill."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SKILL = ROOT / "skills" / "simflow" / "SKILL.md"
CONTRACT = ROOT / "skills" / "simflow" / "router_contract.json"
CAPABILITIES = ROOT / "workflow" / "toolchains" / "capabilities.json"

CANONICAL_STAGES = [
    "literature_review",
    "proposal",
    "modeling",
    "computation",
    "analysis_visualization",
    "writing",
]

ROUTER_FIELDS = [
    "interpreted_intent",
    "recommended_stage",
    "recommended_recipe_tags",
    "recommended_skills",
    "required_evidence",
    "safety_gates",
    "state_write_needed",
    "state_write_reason",
    "next_actions",
    "risks_or_uncertainties",
]


def _skill_text() -> str:
    return SKILL.read_text(encoding="utf-8")


def _contract() -> dict:
    return json.loads(CONTRACT.read_text(encoding="utf-8"))


def _capabilities() -> dict:
    return json.loads(CAPABILITIES.read_text(encoding="utf-8"))


def test_top_level_router_mentions_all_canonical_stages():
    text = _skill_text()
    contract = _contract()

    assert contract["canonical_stages"] == CANONICAL_STAGES
    for stage in CANONICAL_STAGES:
        assert stage in text


def test_top_level_router_is_not_a_centralized_executor_or_domain_parser():
    text = _skill_text().lower()
    contract = _contract()

    assert "not a centralized workflow executor" in text
    assert "domain parser" in text
    assert "submitter" in text
    assert "approval gate" in text
    assert "centralized_executor_behavior" in contract["prohibited_actions"]
    assert "domain_parser_behavior_from_top_level_router" in contract["prohibited_actions"]


def test_state_writes_require_explicit_project_root_and_boundary_rules():
    text = _skill_text()
    lowered = text.lower()
    contract = _contract()

    assert "project_root" in text
    assert "plugin root" in lowered
    assert "mcp server cwd" in lowered
    assert "tool installation directory" in lowered
    assert ".omx" in text
    assert "casual conceptual explanation" in lowered
    assert "route-only answers" in lowered
    assert "initialize_or_track_project" in contract["state_write_triggers"]
    assert "route_only_answer_without_artifact_or_decision" in contract["state_write_non_triggers"]


def test_safety_escalation_routes_high_risk_requests_to_safety_gates():
    text = _skill_text()
    lowered = text.lower()
    contract = _contract()

    assert "simflow-safety-gates" in text
    for phrase in [
        "real local execution",
        "remote execution",
        "hpc submit",
        "sbatch",
        "qsub",
        "srun",
        "mpirun",
        "ssh",
        "credentials",
        "private keys",
        "license files",
        "proprietary files",
        "potcar",
        "destructive operations",
        "bypass dry-run",
    ]:
        assert phrase in lowered
    for trigger in [
        "real_local_execution",
        "remote_execution",
        "hpc_submit",
        "credentials_or_tokens_or_private_keys",
        "vasp_potcar_or_licensed_content",
        "bypass_dry_run_hash_verification_or_approval",
    ]:
        assert trigger in contract["safety_escalation_triggers"]


def test_router_delegates_domain_and_stage_ownership():
    text = _skill_text()

    for skill in [
        "simflow-vasp",
        "simflow-cp2k",
        "simflow-lammps",
        "simflow-gpumd",
        "simflow-mlp",
    ]:
        assert skill in text
    assert "Domain skills own software-specific file semantics" in text
    assert "simflow-computation" in text
    assert "dry-run plans" in text
    assert "submit-readiness evidence" in text
    assert "simflow-analysis-visualization" in text
    assert "simflow-writing" in text
    assert "simflow-verify" in text
    assert "simflow-handoff" in text
    assert "simflow-checkpoint" in text


def test_standard_router_output_fields_are_declared_in_skill_and_contract():
    text = _skill_text()
    contract = _contract()

    assert contract["standard_router_output_fields"] == ROUTER_FIELDS
    for field in ROUTER_FIELDS:
        assert field in text


def test_ambiguous_intent_does_not_default_unknown_tasks_to_known_paths():
    text = _skill_text()
    lowered = text.lower()
    contract = _contract()
    policy = contract["ambiguous_intent_policy"]

    assert "do not default unknown software to a supported helper path" in lowered
    assert "do not default unknown computation tasks to static" in lowered
    assert "energy" in lowered
    assert "nvt" in lowered
    assert "training" in lowered
    assert policy["do_not_default_unknown_software_to_supported_helper"] is True
    assert policy["do_not_default_unknown_computation_tasks_to_known_tasks"] == [
        "static",
        "ENERGY",
        "NVT",
        "training",
    ]


def test_gpumd_nep_contract_reflects_current_toolchain_capabilities():
    text = _skill_text()
    contract = _contract()["gpumd_nep_support_contract"]
    capabilities = _capabilities()

    assert {"gpumd", "nep"} <= set(capabilities["helper_supported_software"])
    assert contract["support_level"] == "helper_supported"
    assert contract["real_submit_allowed"] is False
    for tool in ["gpumd", "nep"]:
        tool_caps = capabilities["capability_support"][tool]
        assert set(contract["supported_capabilities"]) == set(tool_caps["supported"])
        assert set(contract["not_helper_supported"]) == set(tool_caps["not_helper_supported"])
    assert "GPUMD/NEP are helper-supported" in text
    assert "real execution" in text
    assert "HPC submit" in text


def test_router_contract_categories_cover_required_intents():
    contract = _contract()
    categories = {item["category"] for item in contract["routing_categories"]}

    assert categories >= {
        "literature_review",
        "proposal",
        "modeling",
        "vasp_domain",
        "cp2k_domain",
        "lammps_domain",
        "gpumd_nep_domain",
        "mlp_evidence",
        "real_execution_or_submit",
        "analysis_visualization",
        "writing",
        "status_checkpoint_handoff_verify",
        "unknown_or_unsupported_tool_evidence",
    }


def test_router_prohibits_fabrication_and_unsupported_claims():
    text = _skill_text().lower()
    contract = _contract()

    for phrase in [
        "fabricate literature",
        "computation results",
        "datasets",
        "figures",
        "citations",
        "convergence states",
        "job states",
        "production-readiness",
    ]:
        assert phrase in text
    assert "fabricated_literature_results_data_figures_citations_convergence_or_job_states" in contract["prohibited_actions"]
