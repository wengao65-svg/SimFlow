#!/usr/bin/env python3
"""Tests for simflow-intake init_research bootstrap behavior."""

import sys
import tempfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[2] / "skills" / "simflow-intake" / "scripts"
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(ROOT))

from runtime.lib.state import read_state
from init_research import init_research, load_workflow_definition, parse_research_input


def test_load_workflow_definition_dft():
    workflow = load_workflow_definition("dft")
    assert workflow["workflow_type"] == "dft"
    assert workflow["default_entry"] == "literature"
    assert workflow["stages"][0] == "literature"
    assert "literature_review" not in workflow["stages"]


def test_load_workflow_definition_fallback_to_dft():
    workflow = load_workflow_definition("unknown")
    assert workflow["workflow_type"] == "dft"
    assert workflow["default_entry"] == "literature"



def test_parse_research_input_collects_offline_source_inputs():
    parsed = parse_research_input(
        "\n".join([
            "goal: study Si surface",
            "pdfs: papers/a.pdf, papers/b.pdf",
            "bibtex: refs/references.bib",
            "dois: 10.1000/alpha; 10.1000/beta",
            "note: Focus on slab convergence, then adsorption",
            'sources: [{"type": "note", "title": "manual-gap", "text": "Check vacancy formation"}]',
        ])
    )

    assert parsed["source_inputs"]["pdf"] == ["papers/a.pdf", "papers/b.pdf"]
    assert parsed["source_inputs"]["bibtex"] == ["refs/references.bib"]
    assert parsed["source_inputs"]["doi"] == ["10.1000/alpha", "10.1000/beta"]
    assert parsed["source_inputs"]["note"] == ["Focus on slab convergence, then adsorption"]
    assert parsed["source_inputs"]["sources"] == [
        {"type": "note", "title": "manual-gap", "text": "Check vacancy formation"}
    ]


def test_init_research_writes_canonical_metadata_for_dft():
    with tempfile.TemporaryDirectory() as tmpdir:
        result = init_research(
            input_text="goal: study Si surface\nmaterial: Si\nsoftware: vasp\n",
            output_dir=tmpdir,
        )
        sf = Path(tmpdir) / ".simflow"
        metadata = read_state(tmpdir, "metadata.json")
        workflow_state = read_state(tmpdir, "workflow.json")

        assert result["status"] == "success"
        assert result["workflow_type"] == "dft"
        assert result["current_stage"] == "literature"
        assert workflow_state["current_stage"] == "literature"
        assert metadata["workflow_type"] == "dft"
        assert metadata["entry_point"] == "literature"
        assert metadata["current_stage"] == "literature"
        assert metadata["stages"] == [
            "literature",
            "review",
            "proposal",
            "modeling",
            "input_generation",
            "compute",
            "analysis",
            "visualization",
            "writing",
        ]
        assert "literature_review" not in metadata["stages"]
        assert metadata["workflow_definition"].endswith("workflow/workflows/dft.json")
        assert (sf / "state" / "metadata.json").is_file()
        assert not (sf / "state" / "research_metadata.json").exists()
        assert not (sf / "metadata.json").exists()


def test_init_research_uses_workflow_default_entry_for_aimd():
    with tempfile.TemporaryDirectory() as tmpdir:
        result = init_research(
            input_text="goal: run AIMD\nmaterial: H2O\n",
            workflow_type="aimd",
            output_dir=tmpdir,
        )
        metadata = read_state(tmpdir, "metadata.json")
        workflow_state = read_state(tmpdir, "workflow.json")

        assert result["workflow_type"] == "aimd"
        assert result["current_stage"] == "proposal"
        assert workflow_state["current_stage"] == "proposal"
        assert metadata["entry_point"] == "proposal"
        assert metadata["stages"] == [
            "proposal",
            "modeling",
            "input_generation",
            "compute",
            "analysis",
            "visualization",
            "writing",
        ]
        assert metadata["research_sources"]["total_items"] == 0



def test_init_research_writes_normalized_research_sources_to_metadata():
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        pdf_path = project_root / "papers" / "surface.pdf"
        bib_path = project_root / "refs" / "references.bib"
        pdf_path.parent.mkdir(parents=True, exist_ok=True)
        bib_path.parent.mkdir(parents=True, exist_ok=True)
        pdf_path.write_text("pdf placeholder", encoding="utf-8")
        bib_path.write_text("@article{surface, title={Surface Study}}", encoding="utf-8")

        result = init_research(
            input_text="\n".join([
                "goal: study Si surface",
                "material: Si(001)",
                "pdfs: papers/surface.pdf",
                "bibtex: refs/references.bib",
                "dois: 10.1000/alpha, 10.1000/beta",
                "note: Focus on slab convergence first",
                'sources: [{"type": "note", "title": "manual-gap", "text": "Check vacancy formation references"}]',
            ]),
            output_dir=tmpdir,
        )
        metadata = read_state(tmpdir, "metadata.json")
        research_sources = metadata["research_sources"]

        assert result["status"] == "success"
        assert research_sources["counts"] == {"pdf": 1, "bibtex": 1, "doi": 2, "note": 2}
        assert research_sources["total_items"] == 6
        assert research_sources["items"][0]["path"] == "papers/surface.pdf"
        assert research_sources["items"][1]["path"] == "refs/references.bib"
        assert research_sources["items"][2]["doi"] == "10.1000/alpha"
        assert research_sources["items"][5]["label"] == "manual-gap"
