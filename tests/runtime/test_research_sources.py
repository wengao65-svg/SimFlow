#!/usr/bin/env python3
"""Tests for canonical research source normalization."""

import tempfile
from pathlib import Path

from runtime.lib.research_sources import empty_research_source_inputs, normalize_research_sources


def test_normalize_research_sources_returns_empty_bundle_by_default():
    bundle = normalize_research_sources(None, project_root=".")

    assert bundle["bundle_version"] == "1.0"
    assert bundle["counts"] == {"pdf": 0, "bibtex": 0, "doi": 0, "note": 0}
    assert bundle["total_items"] == 0
    assert bundle["items"] == []


def test_normalize_research_sources_mixes_file_doi_and_note_inputs():
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        pdf_path = project_root / "papers" / "surface.pdf"
        bib_path = project_root / "refs" / "references.bib"
        pdf_path.parent.mkdir(parents=True, exist_ok=True)
        bib_path.parent.mkdir(parents=True, exist_ok=True)
        pdf_path.write_text("pdf placeholder", encoding="utf-8")
        bib_path.write_text("@article{test, title={Surface Study}}", encoding="utf-8")

        bundle = normalize_research_sources(
            {
                **empty_research_source_inputs(),
                "pdf": ["papers/surface.pdf"],
                "bibtex": ["refs/references.bib"],
                "doi": ["10.1000/example"],
                "note": ["Track slab convergence assumptions"],
                "sources": [
                    {"type": "doi", "doi": "10.1000/followup", "label": "follow-up"},
                    {"type": "note", "title": "manual-gap", "text": "Check vacancy formation references"},
                ],
            },
            project_root=project_root,
        )

        assert bundle["counts"] == {"pdf": 1, "bibtex": 1, "doi": 2, "note": 2}
        assert bundle["total_items"] == 6
        assert bundle["items"][0] == {
            "source_id": "src_pdf_001",
            "type": "pdf",
            "path": "papers/surface.pdf",
            "label": "surface.pdf",
        }
        assert bundle["items"][1] == {
            "source_id": "src_bibtex_001",
            "type": "bibtex",
            "path": "refs/references.bib",
            "label": "references.bib",
        }
        assert bundle["items"][2]["doi"] == "10.1000/example"
        assert bundle["items"][3]["text"] == "Track slab convergence assumptions"
        assert bundle["items"][4]["label"] == "follow-up"
        assert bundle["items"][5]["label"] == "manual-gap"


def test_normalize_research_sources_rejects_missing_local_files():
    with tempfile.TemporaryDirectory() as tmpdir:
        try:
            normalize_research_sources(
                {**empty_research_source_inputs(), "pdf": ["missing/paper.pdf"]},
                project_root=tmpdir,
            )
        except FileNotFoundError as exc:
            assert "missing/paper.pdf" in str(exc)
        else:
            raise AssertionError("Expected FileNotFoundError for missing research source file")
