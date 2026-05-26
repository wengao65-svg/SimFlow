#!/usr/bin/env python3
"""Tests for canonical project intake bootstrap behavior."""

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from runtime.simflow_core.state import read_state
from runtime.simflow_helpers.project.intake import (
    CANONICAL_STAGE_SEQUENCE,
    canonical_stage_suffix,
    init_research,
    load_workflow_definition,
    normalize_entry_stage,
    parse_research_input,
)


def test_load_workflow_definition_dft():
    workflow = load_workflow_definition("dft")
    assert workflow["workflow_type"] == "dft"
    assert workflow["default_entry"] == "literature_review"
    assert workflow["stages"][0] == "literature_review"
    assert workflow["canonical_stages"][0] == "literature_review"
    assert workflow["path"].endswith("workflow/recipes/dft.json")


def test_load_workflow_definition_fallback_to_dft():
    workflow = load_workflow_definition("unknown")
    assert workflow["workflow_type"] == "dft"
    assert workflow["default_entry"] == "literature_review"



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


def test_parse_research_input_normalizes_entry_stage_aliases():
    parsed = parse_research_input("goal: analyze outputs\nstage: analysis\n")

    assert parsed["entry_stage"] == "analysis_visualization"
    assert parsed["entry_stage_requested"] == "analysis"
    assert normalize_entry_stage("input-generation") == "computation"
    assert normalize_entry_stage("draft") == "writing"
    assert canonical_stage_suffix("modeling") == [
        "modeling",
        "computation",
        "analysis_visualization",
        "writing",
    ]


def test_parse_research_input_rejects_unknown_entry_stage():
    try:
        parse_research_input("goal: test\nentry_stage: invalid_stage\n")
    except ValueError as exc:
        assert "Unknown entry stage" in str(exc)
    else:
        raise AssertionError("Expected ValueError")


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
        assert result["current_stage"] == "literature_review"
        assert workflow_state["current_stage"] == "literature_review"
        assert metadata["workflow_type"] == "dft"
        assert metadata["entry_point"] == "literature_review"
        assert metadata["entry_points"] == [
            "literature_review",
            "proposal",
            "modeling",
            "computation",
            "analysis_visualization",
            "writing",
        ]
        assert metadata["available_entry_points"] == CANONICAL_STAGE_SEQUENCE
        assert metadata["current_stage"] == "literature_review"
        assert metadata["stages"] == [
            "literature_review",
            "proposal",
            "modeling",
            "computation",
            "analysis_visualization",
            "writing",
        ]
        assert "compatibility_activities" not in metadata
        assert metadata["recipe_definition"].endswith("workflow/recipes/dft.json")
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
        assert metadata["available_entry_points"] == CANONICAL_STAGE_SEQUENCE
        assert metadata["stages"] == [
            "proposal",
            "modeling",
            "computation",
            "analysis_visualization",
            "writing",
        ]
        assert metadata["research_sources"]["total_items"] == 0


def test_init_research_accepts_each_canonical_entry_stage():
    for entry_stage in CANONICAL_STAGE_SEQUENCE:
        with tempfile.TemporaryDirectory() as tmpdir:
            result = init_research(
                input_text="goal: enter anywhere\nmaterial: Si\nsoftware: vasp\n",
                entry_stage=entry_stage,
                output_dir=tmpdir,
            )
            metadata = read_state(tmpdir, "metadata.json")
            workflow_state = read_state(tmpdir, "workflow.json")

            assert result["status"] == "success"
            assert result["current_stage"] == entry_stage
            assert workflow_state["current_stage"] == entry_stage
            assert workflow_state["entry_point"] == entry_stage
            assert metadata["entry_point"] == entry_stage
            assert metadata["current_stage"] == entry_stage
            assert metadata["stages"] == canonical_stage_suffix(entry_stage)
            assert metadata["entry_points"] == canonical_stage_suffix(entry_stage)
            assert metadata["available_entry_points"] == CANONICAL_STAGE_SEQUENCE


def test_init_research_entry_stage_argument_overrides_input_text():
    with tempfile.TemporaryDirectory() as tmpdir:
        result = init_research(
            input_text="goal: stage conflict\nstage: proposal\n",
            entry_stage="writing",
            output_dir=tmpdir,
        )
        metadata = read_state(tmpdir, "metadata.json")

        assert result["current_stage"] == "writing"
        assert metadata["entry_point"] == "writing"
        assert metadata["entry_stage_requested"] == "writing"



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
