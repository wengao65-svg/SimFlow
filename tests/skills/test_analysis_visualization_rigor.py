"""Scientific-rigor contract tests for analysis and visualization guidance."""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SKILL_DIR = ROOT / "skills" / "simflow-analysis-visualization"
SKILL = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
RIGOR = (SKILL_DIR / "references" / "analysis_rigor_contract.md").read_text(
    encoding="utf-8"
)
CASES = (SKILL_DIR / "references" / "synthetic_analysis_cases.md").read_text(
    encoding="utf-8"
)


def _normalized(text: str) -> str:
    return " ".join(text.split())


def _case_section(title: str) -> str:
    match = re.search(
        rf"^## {re.escape(title)}\n(?P<body>.*?)(?=^## |\Z)",
        CASES,
        flags=re.MULTILINE | re.DOTALL,
    )
    assert match, title
    return _normalized(match.group("body"))


def test_analysis_contract_is_lightweight_and_claim_bounded():
    combined = _normalized(SKILL + "\n" + RIGOR)

    for phrase in [
        "scientific question",
        "analysis object",
        "comparison object",
        "window and transformation",
        "uncertainty approach",
        "claim level",
        "not a required file, runtime record, or workflow stage",
    ]:
        assert phrase in combined


def test_statistical_unit_contract_rejects_pseudoreplication():
    combined = _normalized(SKILL + "\n" + RIGOR)
    case = _case_section("Statistical Independence")

    for phrase in [
        "Seeds, trajectories, configurations, frames, atoms, and time origins",
        "overlapping time origins",
        "Report both the observation count and independent-unit count",
        "Do not use frame count as `n` for between-run inference",
    ]:
        assert phrase in combined
    assert "reports `n = 1,000,000`" in case
    assert "one independent trajectory" in case
    assert "correlated subsamples" in case


def test_cross_run_and_cross_model_comparison_requires_consistent_basis():
    combined = _normalized(SKILL + "\n" + RIGOR)
    case = _case_section("Comparison Consistency")

    for phrase in [
        "physical quantity and unit conversion",
        "reference zero",
        "sampling conditions",
        "analysis windows",
        "not directly comparable",
    ]:
        assert phrase in combined
    assert "total energy with its own zero" in case
    assert "per atom after subtracting its final frame" in case
    assert "no ranking is claimed" in case


def test_sensitivity_contract_reports_claim_instability():
    combined = _normalized(SKILL + "\n" + RIGOR)
    case = _case_section("Sensitivity")

    for phrase in [
        "equilibration and production windows",
        "cutoff radius",
        "bin width",
        "smoothing bandwidth",
        "fit range",
        "normalization",
        "stable, magnitude-sensitive, sign-sensitive, or unresolved",
    ]:
        assert phrase in combined
    assert "selected after viewing the MSD" in case
    assert "defensible alternatives" in case
    assert "claim strength follows that result" in case


def test_unexpected_result_diagnostic_ladder_precedes_physical_story():
    combined = _normalized(SKILL + "\n" + RIGOR)
    case = _case_section("Unexpected Result")

    ladder = [
        "1. Parsing and identity",
        "2. Units and conventions",
        "3. Calculation health",
        "4. Analysis artifact",
        "5. Sampling",
        "6. Model or method validity",
        "7. Physical interpretation",
    ]
    positions = [RIGOR.index(item) for item in ladder]
    assert positions == sorted(positions)
    assert "described as a phase transition" in case
    assert "before considering a physical transition" in case
    assert "distinguish the hypotheses" in case
    assert "Do not begin with a novel physical explanation" in combined


def test_figure_data_claim_trace_is_bidirectional_and_visual_qa_is_optional():
    combined = _normalized(SKILL + "\n" + RIGOR)
    figure_qa = _normalized(
        (SKILL_DIR / "references" / "figure_contract_and_visual_qa.md").read_text(
            encoding="utf-8"
        )
    )
    case = _case_section("Figure And Claim")

    for phrase in [
        "Figure to data",
        "Data to claim",
        "Claim to figure",
        "Non-claims",
        "Decompose compound captions or claims",
    ]:
        assert phrase in combined
    assert "visually correct and still fail as evidence" in combined
    assert "does not establish universal transferability or mechanism" in case
    assert "Ordinary exploratory plots do not require this review loop" in figure_qa
    assert "final, publication, or handoff" in combined


def test_reference_routing_is_task_specific_and_progressive():
    normalized = _normalized(SKILL)

    routes = {
        "MD structure": "md_structure_analysis.md",
        "diffusion or transport": "md_diffusion_transport.md",
        "electronic structure": "electronic_structure_analysis.md",
        "phonons": "phonon_vibrational_analysis.md",
        "NEB": "neb_barrier_analysis.md",
        "MLP-MD readiness": "mlp_md_analysis_readiness.md",
        "final, publication, or handoff figures": "figure_contract_and_visual_qa.md",
    }
    assert "Load references progressively" in normalized
    for task, reference in routes.items():
        assert task in normalized
        assert reference in normalized


def test_rigor_guidance_does_not_add_runtime_or_execution_ownership():
    combined = (SKILL + "\n" + RIGOR).lower()

    for forbidden in [
        "start_activity",
        "finish_activity",
        "update_stage",
        "session_handoff",
        "create a checkpoint",
        "register an artifact",
        "submit a job",
    ]:
        assert forbidden not in combined
    assert "does not create simflow state" in combined
