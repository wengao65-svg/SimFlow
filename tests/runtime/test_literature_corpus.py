"""Tests for local corpus intake and corpus-first external gap search."""

from pathlib import Path

import pytest

from runtime.simflow_helpers.literature.connectors.base import BaseLiteratureConnector
from runtime.simflow_helpers.literature.corpus import ingest_research_sources, inspect_local_pdf, parse_bibtex
from runtime.simflow_helpers.literature.service import LiteratureService


class CountingConnector(BaseLiteratureConnector):
    provider_name = "openalex"

    def __init__(self, *, search_records=None, metadata_records=None):
        self.search_records = list(search_records or [])
        self.metadata_records = dict(metadata_records or {})
        self.search_calls = 0
        self.search_limits = []
        self.metadata_calls = 0
        self._last_error = None

    def search(self, query, max_results=20, **kwargs):
        self.search_calls += 1
        self.search_limits.append(max_results)
        return self.search_records[:max_results]

    def get_metadata(self, identifier):
        self.metadata_calls += 1
        return self.metadata_records.get(identifier)


class BatchedSearchConnector(CountingConnector):
    def __init__(self, search_batches, **kwargs):
        super().__init__(**kwargs)
        self.search_batches = list(search_batches)

    def search(self, query, max_results=20, **kwargs):
        self.search_calls += 1
        self.search_limits.append(max_results)
        if not self.search_batches:
            return []
        return self.search_batches.pop(0)[:max_results]


def test_parse_bibtex_preserves_nested_braces_and_multiple_entries():
    parsed = parse_bibtex(
        """
        @article{smith2024,
          title = {A {DFT} Study of Silicon},
          author = {Alice Smith and Bob Jones},
          year = {2024},
          doi = {https://doi.org/10.1000/EXAMPLE}
        }
        @misc{preprint,
          title = "Preprint title",
          author = "Carol Lee",
          year = 2023,
          archivePrefix = {arXiv},
          eprint = {2301.01234v2}
        }
        """
    )

    assert parsed["issues"] == []
    assert len(parsed["entries"]) == 2
    assert parsed["entries"][0]["fields"]["title"] == "A {DFT} Study of Silicon"
    assert parsed["entries"][1]["fields"]["eprint"] == "2301.01234v2"


def test_ingest_bibtex_builds_normalized_paper_records(tmp_path):
    bib = tmp_path / "references.bib"
    bib.write_text(
        """
        @article{smith2024,
          title = {A {DFT} Study of Silicon},
          author = {Alice Smith and Bob Jones},
          year = {2024},
          journal = {Physical Review B},
          doi = {https://doi.org/10.1000/EXAMPLE}
        }
        """,
        encoding="utf-8",
    )

    result = ingest_research_sources(
        {"items": [{"source_id": "src_bibtex_001", "type": "bibtex", "path": "references.bib"}]},
        project_root=tmp_path,
    )

    assert result["record_count"] == 1
    record = result["records"][0]
    assert record["title"] == "A DFT Study of Silicon"
    assert record["authors"] == ["Alice Smith", "Bob Jones"]
    assert record["identifiers"] == {"doi": "10.1000/example"}
    assert record["source_pointer"] == "references.bib#smith2024"


def test_local_pdf_is_available_but_never_implicitly_inspected(tmp_path):
    fitz = pytest.importorskip("fitz")
    pdf = tmp_path / "paper.pdf"
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), "Test Paper\nDOI: 10.1000/pdf-test")
    document.set_metadata({"title": "Test Paper", "author": "Alice Smith; Bob Jones"})
    document.save(pdf)
    document.close()

    record, issues = inspect_local_pdf(pdf, project_root=tmp_path)

    assert issues == []
    assert record["title"] == "Test Paper"
    assert record["identifiers"]["doi"] == "10.1000/pdf-test"
    assert record["full_text"]["verified"] is True
    assert record["metadata_extraction"]["full_text_inspected"] is False
    assert record["full_text"]["page_count"] == 1


def test_invalid_pdf_stays_partial_and_reports_header_error(tmp_path):
    pdf = tmp_path / "not-a-paper.pdf"
    pdf.write_text("HTML paywall page", encoding="utf-8")

    record, issues = inspect_local_pdf(pdf, project_root=tmp_path)

    assert record["full_text"]["verified"] is False
    assert issues[0]["code"] == "invalid_pdf_header"


def test_corpus_first_skips_keyword_search_when_local_results_fill_target(tmp_path):
    bib = tmp_path / "references.bib"
    bib.write_text(
        """
        @article{one, title={Silicon DFT convergence}, author={Alice Smith}, year={2024}, doi={10.1000/one}}
        @article{two, title={Silicon DFT surfaces}, author={Bob Jones}, year={2023}, doi={10.1000/two}}
        """,
        encoding="utf-8",
    )
    connector = CountingConnector(metadata_records={
        "10.1000/one": {"doi": "10.1000/one", "title": "Silicon DFT convergence", "source": "OpenAlex"},
        "10.1000/two": {"doi": "10.1000/two", "title": "Silicon DFT surfaces", "source": "OpenAlex"},
    })
    service = LiteratureService([connector])

    result = service.search_with_corpus(
        "silicon DFT",
        {"items": [{"source_id": "src_bibtex_001", "type": "bibtex", "path": "references.bib"}]},
        project_root=str(tmp_path),
        max_results=2,
    )

    assert result["external_search_performed"] is False
    assert result["gap_before_external_search"] == 0
    assert connector.search_calls == 0
    assert connector.metadata_calls == 2
    assert len(result["papers"]) == 2


def test_corpus_first_searches_only_when_local_corpus_has_a_gap(tmp_path):
    bib = tmp_path / "references.bib"
    bib.write_text(
        "@article{one, title={Silicon DFT convergence}, author={Alice Smith}, year={2024}, doi={10.1000/one}}",
        encoding="utf-8",
    )
    connector = CountingConnector(
        search_records=[{"doi": "10.1000/two", "title": "Silicon DFT surfaces", "source": "OpenAlex"}],
        metadata_records={
            "10.1000/one": {"doi": "10.1000/one", "title": "Silicon DFT convergence", "source": "OpenAlex"},
        },
    )
    service = LiteratureService([connector])

    result = service.search_with_corpus(
        "silicon DFT",
        {"items": [{"source_id": "src_bibtex_001", "type": "bibtex", "path": "references.bib"}]},
        project_root=str(tmp_path),
        max_results=2,
    )

    assert result["external_search_performed"] is True
    assert result["gap_before_external_search"] == 1
    assert connector.search_calls == 1
    assert len(result["papers"]) == 2


def test_corpus_doi_is_rescreened_after_metadata_enrichment(tmp_path):
    connector = CountingConnector(
        search_records=[{"doi": "10.1000/relevant", "title": "Silicon DFT surfaces", "source": "OpenAlex"}],
        metadata_records={
            "10.1000/offtopic": {"doi": "10.1000/offtopic", "title": "Clinical trial outcomes", "source": "OpenAlex"},
        },
    )
    service = LiteratureService([connector])

    result = service.search_with_corpus(
        "silicon DFT",
        {"items": [{"source_id": "src_doi_001", "type": "doi", "doi": "10.1000/offtopic"}]},
        project_root=str(tmp_path),
        max_results=1,
    )

    assert result["corpus"]["local_paper_count"] == 0
    assert result["external_search_performed"] is True
    assert [paper["paper_id"] for paper in result["papers"]] == ["doi:10.1000/relevant"]


def test_preprint_to_doi_upgrade_preserves_local_full_text_observation(tmp_path):
    fitz = pytest.importorskip("fitz")
    pdf = tmp_path / "preprint.pdf"
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), "arXiv:2301.01234")
    document.set_metadata({"title": "Silicon DFT preprint", "author": "Alice Smith"})
    document.save(pdf)
    document.close()
    connector = CountingConnector(metadata_records={
        "2301.01234": {
            "doi": "10.1000/published",
            "arxiv_id": "2301.01234",
            "identifiers": {"doi": "10.1000/published", "arxiv": "2301.01234"},
            "title": "Silicon DFT preprint",
            "source": "OpenAlex",
        },
    })
    service = LiteratureService([connector])

    result = service.search_with_corpus(
        "silicon DFT",
        {"items": [{"source_id": "src_pdf_001", "type": "pdf", "path": "preprint.pdf"}]},
        project_root=str(tmp_path),
        max_results=1,
    )

    paper = result["papers"][0]
    assert paper["paper_id"] == "doi:10.1000/published"
    assert paper["identifiers"] == {"arxiv": "2301.01234", "doi": "10.1000/published"}
    assert paper["evidence_level"] == "full_text_available"
    assert paper["provenance"]["sources"] == ["local_pdf", "openalex"]
    assert paper["local_full_text"][0]["verified"] is True


def test_large_pdf_corpus_caps_metadata_queries_and_avoids_keyword_search(tmp_path):
    fitz = pytest.importorskip("fitz")
    items = []
    for index in range(100):
        pdf = tmp_path / f"paper-{index:03d}.pdf"
        document = fitz.open()
        page = document.new_page()
        page.insert_text((72, 72), f"Silicon DFT paper {index}\nDOI: 10.1000/local-{index:03d}")
        document.set_metadata({"title": f"Silicon DFT paper {index}", "author": f"Author {index}"})
        document.save(pdf)
        document.close()
        items.append({"source_id": f"pdf-{index:03d}", "type": "pdf", "path": pdf.name})

    connectors = [CountingConnector(), CountingConnector()]
    result = LiteratureService(connectors).search_with_corpus(
        "silicon DFT",
        {"items": items},
        project_root=str(tmp_path),
        max_results=20,
    )

    assert result["corpus"]["record_count"] == 100
    assert result["corpus"]["local_paper_count"] == 100
    assert len(result["papers"]) == 20
    assert sum(connector.metadata_calls for connector in connectors) == 20
    assert sum(connector.search_calls for connector in connectors) == 0
    assert result["metrics"]["local_target_coverage"] == 1.0
    assert result["metrics"]["local_result_share"] == 1.0
    assert result["metrics"]["duplicate_rate"] == 0.0


def test_gap_search_refills_after_first_round_returns_only_local_duplicate(tmp_path):
    bib = tmp_path / "references.bib"
    bib.write_text(
        "@article{one,title={Silicon DFT convergence},author={Alice Smith},year={2024},doi={10.1000/one}}",
        encoding="utf-8",
    )
    duplicate = {
        "doi": "10.1000/one",
        "title": "Silicon DFT convergence",
        "authors": ["Alice Smith"],
        "year": 2024,
        "source": "OpenAlex",
    }
    new_paper = {
        "doi": "10.1000/two",
        "title": "Silicon DFT surfaces",
        "authors": ["Bob Jones"],
        "year": 2023,
        "source": "OpenAlex",
    }
    connector = BatchedSearchConnector([[duplicate], [new_paper]])

    result = LiteratureService([connector]).search_with_corpus(
        "silicon DFT",
        {"items": [{"source_id": "bib", "type": "bibtex", "path": bib.name}]},
        project_root=str(tmp_path),
        max_results=2,
    )

    assert connector.search_calls == 2
    assert connector.search_limits == [5, 8]
    assert result["external_search_rounds"] == 2
    assert result["gap_after_external_search"] == 0
    assert {paper["paper_id"] for paper in result["papers"]} == {
        "doi:10.1000/one",
        "doi:10.1000/two",
    }
