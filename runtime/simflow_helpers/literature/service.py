"""Multi-source literature search, verification, deduplication, and snowballing."""

from __future__ import annotations

from collections import deque
from difflib import SequenceMatcher
from typing import Any, Iterable

from .evidence import display_evidence_level, initial_evidence_state
from .identity import authors_compatible, canonical_paper_id, identifiers_from_record, match_records, normalize_title
from .models import CitationEdge, PaperRecord, ProviderResult, SourceObservation


SOURCE_PRIORITY = {
    "crossref": 100,
    "local_bibtex": 95,
    "local_doi": 92,
    "local_pdf": 90,
    "openalex": 80,
    "semantic_scholar": 70,
    "arxiv": 60,
    "mock": 0,
}


class LiteratureService:
    """Coordinate multiple existing connectors without owning runtime state."""

    provider_name = "multi_source"

    def __init__(self, connectors: Iterable[Any]):
        self.connectors = [connector for connector in connectors if connector is not None]

    def search(self, query: str, max_results: int = 20, **kwargs: Any) -> list[dict[str, Any]]:
        """Compatibility search returning only merged paper dictionaries."""
        return self.search_papers(query, max_results=max_results, **kwargs)["papers"]

    def get_metadata(self, identifier: str) -> dict[str, Any] | None:
        """Compatibility metadata lookup returning one merged paper dictionary."""
        result = self.verify_metadata(identifier)
        return result["papers"][0] if result["papers"] else None

    def search_papers(
        self,
        query: str,
        *,
        max_results: int = 20,
        seed_records: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Search every provider and merge results with explicit degradation."""
        provider_results = [
            connector.search_result(query, max_results=max_results)
            for connector in self.connectors
        ]
        observations = list(seed_records or [])
        for result in provider_results:
            observations.extend(result.records)
        papers = merge_paper_records(observations)
        papers.sort(key=_search_sort_key)
        papers = papers[:max_results]
        return _operation_result("search", provider_results, papers)

    def search_with_corpus(
        self,
        query: str,
        research_sources: dict[str, Any] | None,
        *,
        project_root: str,
        max_results: int = 20,
        extract_pdf_metadata: bool = True,
    ) -> dict[str, Any]:
        """Screen local corpus first and query providers only for the remaining gap."""
        from .corpus import ingest_research_sources, records_relevant_to_query

        corpus = ingest_research_sources(
            research_sources,
            project_root=project_root,
            extract_pdf_metadata=extract_pdf_metadata,
        )
        relevant = records_relevant_to_query(corpus["records"], query)
        provider_results: list[ProviderResult] = []
        verified_observations = list(relevant)
        verified_identifiers: set[tuple[str, str]] = set()
        for record in relevant:
            identifier = _best_identifier(record)
            if not identifier:
                continue
            identity_key = (canonical_paper_id(record), identifier)
            if identity_key in verified_identifiers:
                continue
            verified_identifiers.add(identity_key)
            for connector in self.connectors:
                metadata_result = connector.metadata_result(identifier)
                provider_results.append(metadata_result)
                verified_observations.extend(metadata_result.records)

        local_papers = records_relevant_to_query(merge_paper_records(verified_observations), query)
        verified_observations = [
            observation
            for observation in verified_observations
            if any(match_records(paper, observation)["match"] for paper in local_papers)
        ]
        gap = max(0, max_results - len(local_papers))
        observations = list(verified_observations)
        if gap:
            provider_limit = min(max_results, max(5, gap * 2))
            search_results = [
                connector.search_result(query, max_results=provider_limit)
                for connector in self.connectors
            ]
            provider_results.extend(search_results)
            for result in search_results:
                observations.extend(result.records)

        papers = merge_paper_records(observations)
        papers.sort(key=_search_sort_key)
        result = _operation_result("corpus_first_search", provider_results, papers[:max_results])
        result["corpus"] = {
            "record_count": corpus["record_count"],
            "relevant_record_count": len(relevant),
            "local_paper_count": len(local_papers),
            "issues": corpus["issues"],
            "source_results": corpus["source_results"],
        }
        result["gap_before_external_search"] = gap
        result["external_search_performed"] = bool(gap)
        result["metadata_cross_checks"] = len(verified_identifiers) * len(self.connectors)
        if not provider_results and papers:
            result["status"] = "success"
        return result

    def verify_metadata(
        self,
        identifier: str,
        *,
        expected: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Cross-check one identifier and retain field-level conflicts."""
        provider_results = [
            connector.metadata_result(identifier)
            for connector in self.connectors
        ]
        observations = [expected] if expected else []
        for result in provider_results:
            observations.extend(result.records)
        papers = merge_paper_records([item for item in observations if item])
        result = _operation_result("metadata", provider_results, papers)
        if expected and papers:
            result["expected_match"] = match_records(expected, papers[0])
            result["expected_validation"] = _validate_expected_metadata(expected, papers[0])
        return result

    def snowball(
        self,
        seed: dict[str, Any] | str,
        *,
        directions: tuple[str, ...] = ("references", "citations"),
        depth: int = 1,
        max_results_per_provider: int = 20,
    ) -> dict[str, Any]:
        """Expand references and cited-by edges with cycle and depth limits."""
        if depth < 1 or depth > 3:
            raise ValueError("Snowball depth must be between 1 and 3")
        invalid = set(directions) - {"references", "citations"}
        if invalid:
            raise ValueError(f"Unsupported snowball direction: {sorted(invalid)[0]}")

        seed_record = seed if isinstance(seed, dict) else {"doi": seed}
        seed_id = canonical_paper_id(seed_record)
        queue = deque([(seed_record, seed_id, 0)])
        visited = {seed_id}
        collected: list[dict[str, Any]] = []
        edges: list[CitationEdge] = []
        provider_results: list[ProviderResult] = []

        while queue:
            current, current_id, current_depth = queue.popleft()
            if current_depth >= depth:
                continue
            identifier = _best_identifier(current)
            if not identifier:
                continue
            for connector in self.connectors:
                for direction in directions:
                    operation = "references" if direction == "references" else "citations"
                    result = (
                        connector.references_result(identifier, max_results_per_provider)
                        if direction == "references"
                        else connector.citations_result(identifier, max_results_per_provider)
                    )
                    provider_results.append(result)
                    for record in result.records:
                        target_id = canonical_paper_id(record)
                        if direction == "references":
                            edge = CitationEdge(current_id, target_id, "references", result.provider, current_depth + 1)
                        else:
                            edge = CitationEdge(target_id, current_id, "cites", result.provider, current_depth + 1)
                        edges.append(edge)
                        collected.append({
                            **record,
                            "discovery": {
                                "method": "snowball",
                                "seed_paper_id": seed_id,
                                "parent_paper_id": current_id,
                                "relation": edge.relation,
                                "provider": result.provider,
                                "depth": current_depth + 1,
                            },
                        })
                        if target_id not in visited:
                            visited.add(target_id)
                            queue.append((record, target_id, current_depth + 1))

        papers = merge_paper_records(collected)
        edge_map = {
            (edge.source_paper_id, edge.target_paper_id, edge.relation, edge.provider, edge.depth): edge
            for edge in edges
        }
        result = _operation_result("snowball", provider_results, papers)
        result["seed_paper_id"] = seed_id
        result["edges"] = [edge.to_dict() for edge in edge_map.values()]
        result["depth"] = depth
        return result


def merge_paper_records(records: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Deduplicate provider/corpus records and retain their observations."""
    groups: list[PaperRecord] = []
    for rank, raw in enumerate(records):
        if not isinstance(raw, dict) or not _has_identity(raw):
            continue
        observation = _observation(raw, rank)
        matches = _find_groups(groups, raw)
        if not matches:
            target = PaperRecord(paper_id=canonical_paper_id(raw))
            groups.append(target)
        else:
            target = matches[0]
            for duplicate in matches[1:]:
                for existing_observation in duplicate.observations:
                    target.observations.append(existing_observation)
                    _merge_observation(target, existing_observation)
                if not target.discovery and duplicate.discovery:
                    target.discovery = dict(duplicate.discovery)
                groups.remove(duplicate)
        target.observations.append(observation)
        _merge_observation(target, observation)
        discovery = raw.get("discovery")
        if isinstance(discovery, dict) and not target.discovery:
            target.discovery = dict(discovery)

    output = []
    for paper in groups:
        full_text_available = any(
            (
                bool(observation.full_text)
                and bool(observation.full_text.get("verified"))
                and bool(observation.full_text.get("path") or observation.full_text.get("url"))
            )
            or any(
                location.get("is_oa") and location.get("pdf_url")
                for location in observation.open_access_locations
            )
            for observation in paper.observations
        )
        paper.evidence = initial_evidence_state(
            observation_count=len({item.source for item in paper.observations}),
            conflicts=paper.conflicts,
            full_text_available=full_text_available,
        )
        result = paper.to_dict()
        result["evidence_level"] = display_evidence_level(paper.evidence)
        result["usable_as_evidence"] = all(
            item.source != "mock" for item in paper.observations
        )
        output.append(result)
    return output


def _find_groups(groups: list[PaperRecord], raw: dict[str, Any]) -> list[PaperRecord]:
    matches = []
    for paper in groups:
        comparison = {
            "title": paper.title,
            "authors": paper.authors,
            "year": paper.year,
            "identifiers": paper.identifiers,
        }
        if match_records(comparison, raw)["match"]:
            matches.append(paper)
    return matches


def _observation(raw: dict[str, Any], rank: int) -> SourceObservation:
    source = _source_key(raw.get("source"))
    return SourceObservation(
        source=source,
        identifiers=identifiers_from_record(raw),
        title=str(raw.get("title") or "").strip(),
        authors=[str(item).strip() for item in raw.get("authors") or [] if str(item).strip()],
        year=_year(raw.get("year") or raw.get("published")),
        venue=str(raw.get("journal") or raw.get("venue") or "").strip(),
        abstract=str(raw.get("abstract") or raw.get("summary") or "").strip(),
        url=str(raw.get("url") or "").strip(),
        citation_count=_int_or_none(raw.get("citation_count") or raw.get("cited_by_count")),
        open_access_locations=list(raw.get("open_access_locations") or []),
        rank=rank,
        source_pointer=str(raw.get("source_pointer") or raw.get("path") or "").strip(),
        full_text=raw.get("full_text") if isinstance(raw.get("full_text"), dict) else None,
        raw=raw,
    )


def _merge_observation(paper: PaperRecord, observation: SourceObservation) -> None:
    for key, value in observation.identifiers.items():
        paper.identifiers.setdefault(key, value)
    if paper.identifiers.get("doi"):
        paper.paper_id = f"doi:{paper.identifiers['doi']}"
    elif paper.identifiers.get("arxiv") and not paper.paper_id.startswith("doi:"):
        paper.paper_id = f"arxiv:{paper.identifiers['arxiv']}"

    for field in ("title", "authors", "year", "venue", "abstract", "citation_count"):
        incoming = getattr(observation, field)
        if incoming in (None, "", []):
            continue
        current = getattr(paper, field)
        if (
            field in {"title", "authors", "year"}
            and current not in (None, "", [])
            and not _values_agree(field, current, incoming)
        ):
            paper.conflicts.append({
                "field": field,
                "selected": current,
                "observed": incoming,
                "source": observation.source,
            })
        current_sources = paper.field_sources.setdefault(field, [])
        current_priority = max((SOURCE_PRIORITY.get(source, 10) for source in current_sources), default=-1)
        incoming_priority = SOURCE_PRIORITY.get(observation.source, 10)
        if current in (None, "", []) or incoming_priority > current_priority:
            setattr(paper, field, incoming)
        if observation.source not in current_sources:
            current_sources.append(observation.source)

    if observation.url and observation.url not in paper.urls:
        paper.urls.append(observation.url)
    for location in observation.open_access_locations:
        key = (location.get("pdf_url"), location.get("landing_page_url"))
        existing = {
            (item.get("pdf_url"), item.get("landing_page_url"))
            for item in paper.open_access_locations
        }
        if key not in existing:
            paper.open_access_locations.append(location)


def _operation_result(
    operation: str,
    provider_results: list[ProviderResult],
    papers: list[dict[str, Any]],
) -> dict[str, Any]:
    errors = [result for result in provider_results if result.status == "error"]
    successful = [result for result in provider_results if result.status == "success"]
    if papers and errors:
        status = "partial"
    elif papers or successful:
        status = "success"
    elif errors and len(errors) == len(provider_results):
        status = "error"
    else:
        status = "empty"
    return {
        "schema_version": "simflow.literature_result.v1",
        "operation": operation,
        "status": status,
        "papers": papers,
        "provider_results": [result.to_dict() for result in provider_results],
        "errors": [
            {"provider": result.provider, "error": result.error, "retryable": result.retryable}
            for result in errors
        ],
    }


def _source_key(value: Any) -> str:
    source = str(value or "unknown").strip().casefold().replace(" ", "_")
    return source.replace("-", "_")


def _has_identity(record: dict[str, Any]) -> bool:
    return bool(record.get("title") or identifiers_from_record(record))


def _year(value: Any) -> int | None:
    try:
        return int(str(value)[:4])
    except (TypeError, ValueError):
        return None


def _int_or_none(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _values_agree(field: str, left: Any, right: Any) -> bool:
    if field == "title":
        left_title = normalize_title(left)
        right_title = normalize_title(right)
        return left_title == right_title or match_records(
            {"title": left, "authors": ["unknown"]},
            {"title": right, "authors": ["unknown"]},
        )["confidence"] >= 0.96
    if field == "year":
        return abs(int(left) - int(right)) <= 1
    if field == "authors":
        return bool(left and right and authors_compatible(left[0], right[0]))
    return normalize_title(left) == normalize_title(right)


def _search_sort_key(paper: dict[str, Any]) -> tuple[int, int, int]:
    ranks = [item.get("rank") for item in paper.get("observations", []) if item.get("rank") is not None]
    best_rank = min(ranks) if ranks else 10**6
    source_count = len({item.get("source") for item in paper.get("observations", [])})
    citations = paper.get("citation_count") or 0
    return (best_rank, -source_count, -citations)


def _best_identifier(record: dict[str, Any]) -> str:
    identifiers = identifiers_from_record(record)
    return (
        identifiers.get("doi")
        or identifiers.get("openalex")
        or identifiers.get("semantic_scholar")
        or identifiers.get("arxiv")
        or ""
    )


def _validate_expected_metadata(expected: dict[str, Any], observed: dict[str, Any]) -> dict[str, Any]:
    """Check expected citation fields independently from identifier equality."""
    checks: dict[str, Any] = {}
    expected_title = normalize_title(expected.get("title"))
    observed_title = normalize_title(observed.get("title"))
    if expected_title:
        score = SequenceMatcher(None, expected_title, observed_title).ratio() if observed_title else 0.0
        checks["title"] = {"status": "match" if score >= 0.90 else "mismatch", "similarity": score}
    expected_year = _year(expected.get("year"))
    observed_year = _year(observed.get("year"))
    if expected_year is not None:
        checks["year"] = {
            "status": "match" if observed_year is not None and abs(expected_year - observed_year) <= 1 else "mismatch",
            "expected": expected_year,
            "observed": observed_year,
        }
    expected_authors = expected.get("authors") or []
    observed_authors = observed.get("authors") or []
    if expected_authors:
        checks["first_author"] = {
            "status": "match"
            if observed_authors and authors_compatible(expected_authors[0], observed_authors[0])
            else "mismatch"
        }
    mismatches = [field for field, check in checks.items() if check["status"] == "mismatch"]
    return {
        "status": "consistent" if not mismatches else "conflicted",
        "checks": checks,
        "mismatches": mismatches,
    }


__all__ = ["LiteratureService", "merge_paper_records"]
