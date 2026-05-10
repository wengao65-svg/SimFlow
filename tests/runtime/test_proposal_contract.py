#!/usr/bin/env python3
"""Tests for runtime/lib/proposal_contract.py."""

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INTAKE_DIR = ROOT / "skills" / "simflow-intake" / "scripts"
LITERATURE_DIR = ROOT / "skills" / "simflow-literature" / "scripts"
REVIEW_DIR = ROOT / "skills" / "simflow-review" / "scripts"
PROPOSAL_DIR = ROOT / "skills" / "simflow-proposal" / "scripts"

sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "runtime"))
sys.path.insert(0, str(INTAKE_DIR))
sys.path.insert(0, str(LITERATURE_DIR))
sys.path.insert(0, str(REVIEW_DIR))
sys.path.insert(0, str(PROPOSAL_DIR))

from runtime.lib.artifact import list_artifacts
from runtime.lib.proposal_contract import load_proposal_contract
from generate_literature_matrix import generate_literature_matrix
from generate_proposal import generate_proposal
from generate_review import generate_review
from init_research import init_research


def _prepare_proposal(tmpdir: str, *, software: str = "vasp", parameters: str = '{"encut": 520, "kmesh": "4x4x1"}') -> Path:
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
            f"software: {software}",
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
        assert contract["output_roots"]["reports"] == ".simflow/reports"
        assert "# Proposal" in contract["proposal_markdown"]


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


def test_load_proposal_contract_rejects_unsupported_software():
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = _prepare_proposal(tmpdir, software="qe")

        try:
            load_proposal_contract(str(project_root / ".simflow"))
        except ValueError as exc:
            assert str(exc) == "Unsupported software for Milestone C: qe"
        else:
            raise AssertionError("Expected ValueError")
