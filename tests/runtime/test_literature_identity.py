"""Tests for canonical paper identity and evidence boundaries."""

import pytest

from runtime.simflow_helpers.literature.evidence import (
    display_evidence_level,
    initial_evidence_state,
    mark_claim_verified,
    mark_full_text_available,
    mark_full_text_inspected,
)
from runtime.simflow_helpers.literature.identity import (
    authors_compatible,
    canonical_paper_id,
    match_records,
    normalize_arxiv_id,
    normalize_doi,
    normalize_title,
)


def test_identifier_normalization_handles_urls_case_and_arxiv_versions():
    assert normalize_doi("https://doi.org/10.1038/S41586-021-03819-2") == "10.1038/s41586-021-03819-2"
    assert normalize_doi("doi: 10.1000/Test.1") == "10.1000/test.1"
    assert normalize_arxiv_id("https://arxiv.org/pdf/2301.01234v3.pdf") == "2301.01234"
    assert normalize_arxiv_id("arXiv:2301.01234v3", keep_version=True) == "2301.01234v3"


def test_identity_prefers_doi_then_arxiv():
    assert canonical_paper_id({"doi": "10.1000/example"}) == "doi:10.1000/example"
    assert canonical_paper_id({"arxiv_id": "2301.01234v2"}) == "arxiv:2301.01234"


def test_title_only_similarity_never_auto_merges():
    result = match_records(
        {"title": "A reliable simulation workflow", "authors": ["Alice Smith"], "year": 2024},
        {"title": "A reliable simulation workflow", "authors": ["Bob Jones"], "year": 2024},
    )

    assert result["match"] is False
    assert result["reason"] == "title_only_candidate"


def test_conflicting_strong_identifiers_never_merge_even_with_same_title():
    result = match_records(
        {"doi": "10.1000/one", "title": "Same title", "authors": ["Alice Smith"], "year": 2024},
        {"doi": "10.1000/two", "title": "Same title", "authors": ["Alice Smith"], "year": 2024},
    )

    assert result == {"match": False, "confidence": 0.0, "reason": "conflicting_doi"}


def test_non_latin_titles_retain_searchable_identity():
    assert normalize_title("第一性原理计算") == "第一性原理计算"


def test_title_author_year_can_merge_without_identifiers():
    result = match_records(
        {"title": "A reliable simulation workflow", "authors": ["Alice Smith"], "year": 2024},
        {"title": "A Reliable Simulation Workflow", "authors": ["A. Smith"], "year": 2025},
    )

    assert result["match"] is True
    assert result["reason"] == "title_author_year"


def test_author_compatibility_accepts_surname_only_and_initials():
    assert authors_compatible("Jumper", "John Jumper") is True
    assert authors_compatible("A. Smith", "Alice Smith") is True
    assert authors_compatible("Alice Smith", "Bob Jones") is False


def test_evidence_boundaries_require_explicit_inspection_and_claim_locators():
    state = initial_evidence_state(observation_count=2)
    assert display_evidence_level(state) == "metadata_only"

    state = mark_full_text_available(
        state,
        {"path": "papers/example.pdf", "access_basis": "user_provided"},
    )
    assert display_evidence_level(state) == "full_text_available"

    with pytest.raises(ValueError, match="locators"):
        mark_full_text_inspected(state, locators=[])

    state = mark_full_text_inspected(state, locators=["p. 4", "Methods"])
    assert display_evidence_level(state) == "full_text_inspected"

    state = mark_claim_verified(
        state,
        claim="The calculation used a 500 eV cutoff.",
        locators=["Methods, p. 4"],
    )
    assert display_evidence_level(state) == "claim_verified"


def test_claim_cannot_be_verified_from_metadata_or_available_pdf_only():
    state = mark_full_text_available(
        initial_evidence_state(),
        {"url": "https://example.org/paper.pdf", "access_basis": "open_access"},
    )

    with pytest.raises(ValueError, match="inspected full text"):
        mark_claim_verified(state, claim="claim", locators=["p. 1"])
