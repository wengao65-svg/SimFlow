#!/usr/bin/env python3
"""Tests for runtime/lib/proposal_contract.py."""

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LITERATURE_DIR = ROOT / "skills" / "simflow-literature-review" / "scripts"
REVIEW_DIR = ROOT / "skills" / "simflow-literature-review" / "scripts"
PROPOSAL_DIR = ROOT / "skills" / "simflow-proposal" / "scripts"

sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "runtime"))
sys.path.insert(0, str(LITERATURE_DIR))
sys.path.insert(0, str(REVIEW_DIR))
sys.path.insert(0, str(PROPOSAL_DIR))

from runtime.simflow_core.artifacts import list_artifacts
from runtime.simflow_core.proposals import load_proposal_contract
from generate_literature_matrix import generate_literature_matrix
from generate_proposal import generate_proposal
from generate_review import generate_review
from runtime.simflow_helpers.project.intake import init_research


def _prepare_proposal(
    tmpdir: str,
    *,
    software: str = "vasp",
    workflow_type: str = "dft",
    parameters: str = '{"encut": 520, "kmesh": "4x4x1"}',
    toolchain: str | None = None,
) -> Path:
    project_root = Path(tmpdir)
    pdf_path = project_root / "papers" / "surface.pdf"
    bib_path = project_root / "refs" / "references.bib"
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    bib_path.parent.mkdir(parents=True, exist_ok=True)
    pdf_path.write_text("pdf placeholder", encoding="utf-8")
    bib_path.write_text("@article{surface, title={Surface Study}}", encoding="utf-8")

    init_research(
        input_text="\n".join([
            "goal: study Si surface reconstruction",
            "material: Si(001)",
            f"method: {workflow_type}",
            f"software: {software}",
            *([f"toolchain: {toolchain}"] if toolchain else []),
            f"parameters: {parameters}",
            "pdfs: papers/surface.pdf",
            "bibtex: refs/references.bib",
            "dois: 10.1000/alpha",
            "note: Focus on dimer buckling evidence",
        ]),
        output_dir=tmpdir,
    )
    generate_literature_matrix(str(project_root / ".simflow"))
    generate_review(str(project_root / ".simflow"))
    result = generate_proposal(str(project_root / ".simflow"))
    assert result["status"] == "success"
    return project_root


def test_load_proposal_contract_normalizes_registered_artifacts():
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = _prepare_proposal(tmpdir)

        contract = load_proposal_contract(str(project_root / ".simflow"))
        proposal_artifacts = list_artifacts(stage="proposal", project_root=tmpdir)

        assert contract["workflow_type"] == "dft"
        assert contract["software"] == "vasp"
        assert contract["material"] == "Si(001)"
        assert contract["research_goal"] == "study Si surface reconstruction"
        assert contract["job_type"] is None
        assert contract["task"] is None
        assert contract["structure_hints"] == {"material": "Si(001)"}
        assert contract["parameter_overrides"] == {"encut": 520, "kmesh": "4x4x1"}
        assert len(contract["parameter_rows"]) == 5
        assert contract["research_questions"][0]["category"] == "goal"
        assert contract["research_questions"][1]["parameter_keys"] == ["encut", "kmesh"]
        assert contract["proposal_artifacts"]["research_questions.json"]["artifact_id"] == proposal_artifacts[2]["artifact_id"]
        assert contract["proposal_artifacts"]["proposal_contract.json"]["artifact_id"] == proposal_artifacts[3]["artifact_id"]
        assert contract["proposal_artifacts"]["protocol_contract.json"]["artifact_id"] == proposal_artifacts[4]["artifact_id"]
        assert contract["output_roots"]["reports"] == ".simflow/reports"
        assert "# Proposal" in contract["proposal_markdown"]
        assert "## Protocol Outline" in contract["proposal_markdown"]
        assert contract["calculation_plan"]["dry_run_first"] is True
        assert contract["resource_assumptions"]["real_submit"] is False
        assert contract["protocol_contract"]["schema_version"] == "protocol_contract.v1"
        assert contract["protocol_contract"]["objective"]["material"] == "Si(001)"
        assert contract["protocol_contract"]["dry_run_requirements"]["dry_run_first"] is True
        assert contract["protocol_contract"]["dry_run_requirements"]["real_submit_requires_approval"] is True
        assert len(contract["protocol_contract"]["ordered_steps"]) == 4
        assert len(contract["protocol_contract"]["acceptance_gates"]) == 4
        assert contract["source_artifact_ids"]
        assert len(contract["decision_criteria"]) == 3
        assert len(contract["risk_register"]) == 2


def test_generate_proposal_registers_protocol_contract_artifact():
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = _prepare_proposal(tmpdir)

        artifacts = list_artifacts(stage="proposal", project_root=tmpdir)
        by_name = {artifact["name"]: artifact for artifact in artifacts}
        protocol_path = project_root / ".simflow" / "plans" / "protocol_contract.json"
        protocol = json.loads(protocol_path.read_text(encoding="utf-8"))

        assert "protocol_contract.json" in by_name
        assert by_name["protocol_contract.json"]["type"] == "protocol_contract"
        assert by_name["protocol_contract.json"]["metadata"]["evidence_keys"] == [
            "ordered_steps",
            "acceptance_gates",
            "dry_run_requirements",
        ]
        assert protocol["inputs"][4]["name"] == "literature_evidence"
        assert protocol["inputs"][4]["status"] == "provided"
        assert protocol["control_groups"][0]["status"] == "needs_definition"


def test_load_proposal_contract_allows_missing_protocol_contract_artifact_for_old_projects():
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = _prepare_proposal(tmpdir)
        protocol_path = project_root / ".simflow" / "plans" / "protocol_contract.json"
        protocol_path.unlink()
        artifacts_path = project_root / ".simflow" / "state" / "artifacts.json"
        artifacts = json.loads(artifacts_path.read_text(encoding="utf-8"))
        artifacts = [artifact for artifact in artifacts if artifact.get("name") != "protocol_contract.json"]
        artifacts_path.write_text(json.dumps(artifacts, indent=2), encoding="utf-8")

        contract = load_proposal_contract(str(project_root / ".simflow"))

        assert contract["protocol_contract"] == {}
        assert "protocol_contract.json" not in contract["proposal_artifacts"]


def test_load_proposal_contract_uses_metadata_over_parameter_table_values():
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = _prepare_proposal(tmpdir)
        parameter_table_path = project_root / ".simflow" / "plans" / "parameter_table.csv"
        rows = parameter_table_path.read_text(encoding="utf-8")
        parameter_table_path.write_text(rows.replace("vasp", "cp2k", 1), encoding="utf-8")

        contract = load_proposal_contract(str(project_root / ".simflow"))

        assert contract["software"] == "vasp"


def test_load_proposal_contract_errors_when_research_questions_artifact_is_missing():
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = _prepare_proposal(tmpdir)
        questions_path = project_root / ".simflow" / "plans" / "research_questions.json"
        questions_path.unlink()

        try:
            load_proposal_contract(str(project_root / ".simflow"))
        except FileNotFoundError as exc:
            assert str(questions_path) in str(exc)
        else:
            raise AssertionError("Expected FileNotFoundError")


def test_load_proposal_contract_tracks_qe_alias_without_blocking_workflow():
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = _prepare_proposal(tmpdir, software="qe")

        contract = load_proposal_contract(str(project_root / ".simflow"))

        assert contract["software"] == "quantum_espresso"
        assert contract["helper_support"]["tracked_only"] == ["quantum_espresso"]
        assert contract["helper_support"]["support_levels"]["quantum_espresso"] == "tracked_only"
        assert contract["toolchain_plan"]["activities"]["primary"] == ["quantum_espresso"]


def test_non_mlp_recipes_share_optional_toolchain_support_contract():
    scenarios = [
        ("dft", "quantum_espresso", "tracked_only"),
        ("aimd", "cp2k", "helper_supported"),
        ("classical_md", "gromacs", "tracked_only"),
    ]
    for workflow_type, software, support_level in scenarios:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = _prepare_proposal(
                tmpdir,
                workflow_type=workflow_type,
                software=software,
            )

            contract = load_proposal_contract(str(project_root / ".simflow"))

            assert contract["workflow_type"] == workflow_type
            assert contract["software"] == software
            assert contract["helper_support"]["support_levels"][software] == support_level
            assert contract["toolchain_plan"]["activities"]["primary"] == [software]


def test_mlp_md_contract_tracks_non_helper_toolchain_without_helper_support():
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = _prepare_proposal(
            tmpdir,
            software="gpumd",
            workflow_type="mlp_md",
            parameters='{"dataset_split": "90/10"}',
            toolchain="cp2k, vasp, gpumd, nep, neptrainkit",
        )
        contract = load_proposal_contract(str(project_root / ".simflow"))
        protocol = contract["protocol_contract"]
        artifacts = list_artifacts(stage="proposal", project_root=tmpdir)
        protocol_artifact = next(artifact for artifact in artifacts if artifact["name"] == "protocol_contract.json")

        assert contract["workflow_type"] == "mlp_md"
        assert contract["software"] == "gpumd"
        assert contract["toolchain"] == ["gpumd", "cp2k", "vasp", "nep", "neptrainkit"]
        assert contract["software_support"]["builtin_helpers"] == ["cp2k", "vasp"]
        assert contract["software_support"]["tracked_only"] == ["gpumd", "nep", "neptrainkit"]
        assert contract["helper_support"]["support_levels"]["gpumd"] == "tracked_only"
        assert contract["toolchain_plan"]["activities"]["labeling"] == ["cp2k", "vasp"]
        assert contract["toolchain_plan"]["activities"]["training"] == ["gpumd", "nep"]
        assert protocol["toolchain"] == ["gpumd", "cp2k", "vasp", "nep", "neptrainkit"]
        assert protocol["software_support"]["tracked_only"] == ["gpumd", "nep", "neptrainkit"]
        assert protocol["toolchain_plan"]["activities"]["selection"] == ["neptrainkit"]
        assert protocol["inputs"][-1]["name"] == "toolchain"
        assert protocol["inputs"][-1]["required"] is True
        assert protocol_artifact["metadata"]["recipe"] == "mlp_md"
        assert protocol_artifact["metadata"]["toolchain"] == ["gpumd", "cp2k", "vasp", "nep", "neptrainkit"]


def test_load_proposal_contract_accepts_lammps_direct_entry_metadata():
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        init_research(
            input_text="\n".join([
                "entry_stage: computation",
                "goal: prepare LAMMPS dry-run evidence",
                "material: Si",
                "software: lammps",
                "parameters: {\"input_files\": [\"in.lammps\", \"data.lammps\"], \"task\": \"nvt\"}",
            ]),
            output_dir=tmpdir,
        )

        contract = load_proposal_contract(str(project_root / ".simflow"), allow_direct_entry=True)

        assert contract["software"] == "lammps"
        assert contract["task"] == "nvt"
        assert contract["direct_entry"] is True
        assert contract["protocol_contract"] == {}


def test_load_proposal_contract_can_use_direct_modeling_entry_metadata():
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        init_research(
            input_text="\n".join([
                "entry_stage: modeling",
                "goal: build Si model from supplied parameters",
                "material: Si",
                "software: vasp",
                "parameters: {\"structure_type\": \"diamond\", \"lattice_param\": 5.43, \"elements\": [\"Si\"]}",
            ]),
            output_dir=tmpdir,
        )

        contract = load_proposal_contract(str(project_root / ".simflow"), allow_direct_entry=True)

        assert contract["direct_entry"] is True
        assert contract["proposal_artifacts"] == {}
        assert contract["source_artifact_ids"] == []
        assert contract["literature_evidence_summary"]["status"] == "not_provided"
        assert contract["structure_hints"]["structure_type"] == "diamond"
        assert contract["protocol_contract"] == {}


def test_generate_proposal_direct_entry_protocol_marks_missing_literature():
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        init_research(
            input_text="\n".join([
                "entry_stage: proposal",
                "goal: compare vacancy formation energies",
                "material: Si",
                "software: vasp",
                "parameters: {\"supercell\": \"2x2x2\", \"defect\": \"vacancy\"}",
            ]),
            output_dir=tmpdir,
        )

        result = generate_proposal(str(project_root / ".simflow"))
        protocol = json.loads(Path(result["output_files"]["protocol_contract"]).read_text(encoding="utf-8"))

        assert result["status"] == "success"
        assert protocol["evidence_limits"]["literature_status"] == "not_provided"
        assert protocol["evidence_limits"]["claims_policy"].startswith("Treat literature-dependent claims as unverified")
        literature_input = next(item for item in protocol["inputs"] if item["name"] == "literature_evidence")
        assert literature_input["status"] == "not_provided"
        assert protocol["dry_run_requirements"]["dry_run_first"] is True
        assert protocol["failure_branches"][0]["condition"] == "required_inputs_or_literature_evidence_missing"
