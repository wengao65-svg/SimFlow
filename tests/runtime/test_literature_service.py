"""Tests for multi-source collaboration, deduplication, and snowball search."""

from runtime.simflow_helpers.literature.connectors.base import BaseLiteratureConnector
from runtime.simflow_helpers.literature.models import ProviderResult
from runtime.simflow_helpers.literature.service import LiteratureService, merge_paper_records


class FakeConnector(BaseLiteratureConnector):
    def __init__(self, name, *, search_records=None, metadata_record=None, fail_search=False, references=None, citations=None):
        self.provider_name = name
        self.search_records = list(search_records or [])
        self.metadata_record = metadata_record
        self.fail_search = fail_search
        self.reference_records = list(references or [])
        self.citation_records = list(citations or [])
        self.search_calls = 0
        self.metadata_calls = 0
        self._last_error = None

    def search(self, query, max_results=20, **kwargs):
        self.search_calls += 1
        if self.fail_search:
            raise TimeoutError(f"{self.provider_name} timed out")
        return self.search_records[:max_results]

    def get_metadata(self, doi):
        self.metadata_calls += 1
        return self.metadata_record

    def references_result(self, identifier, max_results=20):
        return ProviderResult(self.provider_name, "references", "success", self.reference_records[:max_results])

    def citations_result(self, identifier, max_results=20):
        return ProviderResult(self.provider_name, "citations", "success", self.citation_records[:max_results])


def test_multi_source_search_merges_duplicate_doi_and_retains_field_provenance():
    service = LiteratureService([
        FakeConnector("openalex", search_records=[{
            "doi": "10.1000/example",
            "title": "Unified Paper",
            "authors": ["Alice Smith"],
            "year": 2024,
            "citation_count": 10,
            "source": "OpenAlex",
        }]),
        FakeConnector("crossref", search_records=[{
            "doi": "https://doi.org/10.1000/EXAMPLE",
            "title": "Unified Paper",
            "authors": ["Alice Smith"],
            "year": 2024,
            "journal": "Journal of Tests",
            "source": "Crossref",
        }]),
    ])

    result = service.search_papers("unified", max_results=10)

    assert result["status"] == "success"
    assert len(result["papers"]) == 1
    paper = result["papers"][0]
    assert paper["paper_id"] == "doi:10.1000/example"
    assert {item["source"] for item in paper["observations"]} == {"openalex", "crossref"}
    assert paper["evidence"]["metadata"] == "cross_checked"
    assert paper["venue"] == "Journal of Tests"


def test_multi_source_search_reports_partial_success_when_one_provider_fails():
    service = LiteratureService([
        FakeConnector("openalex", search_records=[{"doi": "10.1000/example", "title": "Paper", "source": "OpenAlex"}]),
        FakeConnector("crossref", fail_search=True),
    ])

    result = service.search_papers("paper")

    assert result["status"] == "partial"
    assert len(result["papers"]) == 1
    assert result["errors"] == [{
        "provider": "crossref",
        "error": "crossref timed out",
        "retryable": True,
    }]


def test_same_doi_with_conflicting_title_is_merged_but_flagged():
    papers = merge_paper_records([
        {"doi": "10.1000/example", "title": "Correct title", "source": "Crossref"},
        {"doi": "10.1000/example", "title": "Different work", "source": "OpenAlex"},
    ])

    assert len(papers) == 1
    assert papers[0]["title"] == "Correct title"
    assert papers[0]["evidence"]["metadata"] == "conflicted"
    assert papers[0]["conflicts"][0]["field"] == "title"


def test_bridge_record_coalesces_existing_doi_and_arxiv_groups():
    papers = merge_paper_records([
        {"doi": "10.1000/published", "source": "Crossref"},
        {"arxiv_id": "2301.01234", "source": "arXiv"},
        {
            "doi": "10.1000/published",
            "arxiv_id": "2301.01234v2",
            "title": "Unified preprint and publication",
            "source": "OpenAlex",
        },
    ])

    assert len(papers) == 1
    assert papers[0]["paper_id"] == "doi:10.1000/published"
    assert papers[0]["identifiers"] == {
        "doi": "10.1000/published",
        "arxiv": "2301.01234",
    }
    assert {item["source"] for item in papers[0]["observations"]} == {
        "crossref",
        "arxiv",
        "openalex",
    }


def test_expected_provider_variations_do_not_create_identity_conflicts():
    papers = merge_paper_records([
        {
            "doi": "10.1000/example",
            "title": "Same paper",
            "authors": ["Alice Smith", "Bob Jones"],
            "year": 2024,
            "journal": "Journal of Tests",
            "abstract": "Long abstract from one source.",
            "citation_count": 10,
            "source": "Crossref",
        },
        {
            "doi": "10.1000/example",
            "title": "Same Paper",
            "authors": ["A. Smith"],
            "year": 2024,
            "venue": "J. Tests",
            "abstract": "Short abstract.",
            "citation_count": 12,
            "source": "OpenAlex",
        },
    ])

    assert papers[0]["conflicts"] == []
    assert papers[0]["evidence"]["metadata"] == "cross_checked"


def test_invalid_local_pdf_is_not_promoted_to_full_text_available():
    papers = merge_paper_records([{
        "title": "Broken PDF",
        "source": "local_pdf",
        "full_text": {
            "path": "papers/broken.pdf",
            "access_basis": "user_provided",
            "verified": False,
        },
    }])

    assert papers[0]["evidence_level"] == "metadata_only"
    assert papers[0]["evidence"]["full_text"] == "unavailable"


def test_metadata_verification_detects_doi_title_mismatch():
    service = LiteratureService([
        FakeConnector("crossref", metadata_record={
            "doi": "10.1000/example",
            "title": "Observed title",
            "authors": ["Alice Smith"],
            "year": 2024,
            "source": "Crossref",
        })
    ])

    result = service.verify_metadata(
        "10.1000/example",
        expected={"doi": "10.1000/example", "title": "Completely unrelated title", "authors": ["Bob Jones"], "year": 2018},
    )

    assert result["expected_validation"]["status"] == "conflicted"
    assert set(result["expected_validation"]["mismatches"]) == {"title", "year", "first_author"}


def test_snowball_deduplicates_edges_and_prevents_cycles():
    cited = {"doi": "10.1000/cited", "title": "Cited", "source": "OpenAlex"}
    citing = {"doi": "10.1000/citing", "title": "Citing", "source": "OpenAlex"}
    service = LiteratureService([
        FakeConnector("openalex", references=[cited, cited], citations=[citing])
    ])

    result = service.snowball(
        {"doi": "10.1000/seed", "title": "Seed"},
        depth=1,
        max_results_per_provider=10,
    )

    assert result["status"] == "success"
    assert {paper["paper_id"] for paper in result["papers"]} == {"doi:10.1000/cited", "doi:10.1000/citing"}
    assert len(result["edges"]) == 2
    assert {edge["relation"] for edge in result["edges"]} == {"references", "cites"}
