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
        include_diagnostics: bool = False,
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
        selected_papers = papers[:max_results]
        return _operation_result(
            "search",
            provider_results,
            selected_papers,
            observation_count=len(observations),
            metrics_papers=papers,
            include_diagnostics=include_diagnostics,
        )

    def search_with_corpus(
        self,
        query: str,
        research_sources: dict[str, Any] | None,
        *,
        project_root: str,
        max_results: int = 20,
        extract_pdf_metadata: bool = True,
        max_metadata_queries: int | None = None,
        max_external_search_rounds: int = 2,
        include_diagnostics: bool = False,
    ) -> dict[str, Any]:
        """Screen local corpus first and query providers only for the remaining gap."""
        from .corpus import ingest_research_sources, records_relevant_to_query

        if max_results < 1:
            raise ValueError("max_results must be positive")
        if max_external_search_rounds < 0:
            raise ValueError("max_external_search_rounds cannot be negative")
        metadata_budget = max_results if max_metadata_queries is None else max_metadata_queries
        if metadata_budget < 0:
            raise ValueError("max_metadata_queries cannot be negative")

        corpus = ingest_research_sources(
            research_sources,
            project_root=project_root,
            extract_pdf_metadata=extract_pdf_metadata,
        )
        relevant = records_relevant_to_query(corpus["records"], query)
        provider_results: list[ProviderResult] = []
        verified_observations = list(relevant)
        verified_identifiers: set[str] = set()
        metadata_queries = 0
        verification_candidates = sorted(relevant, key=_corpus_verification_sort_key)
        for record in verification_candidates:
            identifier = _best_identifier(record)
            if not identifier or identifier in verified_identifiers:
                continue
            verified_identifiers.add(identifier)
            for connector in self.connectors:
                if metadata_queries >= metadata_budget:
                    break
                metadata_result = connector.metadata_result(identifier)
                provider_results.append(metadata_result)
                verified_observations.extend(metadata_result.records)
                metadata_queries += metadata_result.query_count
            if metadata_queries >= metadata_budget:
                break

        local_papers = records_relevant_to_query(merge_paper_records(verified_observations), query)
        verified_observations = [
            observation
            for paper in local_papers
            for observation in paper.get("observations", [])
        ]
        gap = max(0, max_results - len(local_papers))
        observations = list(verified_observations)
        external_search_rounds = 0
        papers = merge_paper_records(observations)
        papers.sort(key=_search_sort_key)
        while gap and external_search_rounds < max_external_search_rounds and self.connectors:
            round_number = external_search_rounds + 1
            provider_limit = min(
                max(5, max_results * 4),
                max(5 * round_number, gap * (2 ** round_number)),
            )
            search_results = [
                connector.search_result(query, max_results=provider_limit)
                for connector in self.connectors
            ]
            provider_results.extend(search_results)
            for result in search_results:
                observations.extend(result.records)
            external_search_rounds += 1
            papers = merge_paper_records(observations)
            papers.sort(key=_search_sort_key)
            gap = max(0, max_results - len(papers))

        selected_papers = papers[:max_results]
        result = _operation_result(
            "corpus_first_search",
            provider_results,
            selected_papers,
            observation_count=len(observations),
            metrics_papers=papers,
            include_diagnostics=include_diagnostics,
        )
        local_result_count = sum(
            1
            for paper in selected_papers
            if any(
                observation.get("source", "").startswith("local_")
                for observation in paper.get("observations", [])
            )
        )
        result["corpus"] = {
            "record_count": corpus["record_count"],
            "relevant_record_count": len(relevant),
            "local_paper_count": len(local_papers),
            "issues": corpus["issues"],
            "source_results": corpus["source_results"],
        }
        initial_gap = max(0, max_results - len(local_papers))
        result["gap_before_external_search"] = initial_gap
        result["gap_after_external_search"] = max(0, max_results - len(selected_papers))
        result["external_search_performed"] = external_search_rounds > 0
        result["external_search_rounds"] = external_search_rounds
        result["metadata_cross_checks"] = metadata_queries
        result["metrics"].update({
            "metadata_query_count": sum(
                item.query_count for item in provider_results if item.operation == "metadata"
            ),
            "search_query_count": sum(
                item.query_count for item in provider_results if item.operation == "search"
            ),
            "local_corpus_record_count": corpus["record_count"],
            "local_relevant_record_count": len(relevant),
            "local_paper_count": len(local_papers),
            "local_result_count": local_result_count,
            "local_corpus_hit_rate": len(relevant) / corpus["record_count"] if corpus["record_count"] else 0.0,
            "local_target_coverage": min(len(local_papers), max_results) / max_results,
            "local_result_share": local_result_count / len(selected_papers) if selected_papers else 0.0,
        })
        if not provider_results and papers:
            result["status"] = "success"
        return result

    def verify_metadata(
        self,
        identifier: str,
        *,
        expected: dict[str, Any] | None = None,
        include_diagnostics: bool = False,
    ) -> dict[str, Any]:
        """Cross-check one identifier and retain field-level conflicts."""
        provider_results = [
            connector.metadata_result(identifier)
            for connector in self.connectors
        ]
        observations = []
        for result in provider_results:
            observations.extend(result.records)
        papers = merge_paper_records(observations)
        result = _operation_result(
            "metadata",
            provider_results,
            papers,
            observation_count=len(observations),
            include_diagnostics=include_diagnostics,
        )
        if expected and papers:
            observed = _paper_for_expected(expected, papers)
            result["expected_match"] = match_records(expected, observed)
            result["expected_validation"] = _validate_expected_metadata(expected, observed)
        return result

    def snowball(
        self,
        seed: dict[str, Any] | str,
        *,
        directions: tuple[str, ...] = ("references", "citations"),
        depth: int = 1,
        max_results_per_provider: int = 10,
        mode: str = "focused",
        max_papers: int = 50,
        max_edges: int = 100,
        max_provider_operations: int = 16,
        max_external_queries: int = 32,
        max_frontier: int = 25,
        include_diagnostics: bool = False,
    ) -> dict[str, Any]:
        """Expand references and cited-by edges with cycle and depth limits."""
        if depth < 1 or depth > 3:
            raise ValueError("Snowball depth must be between 1 and 3")
        if mode not in {"focused", "systematic_review", "method_lineage"}:
            raise ValueError(f"Unsupported snowball mode: {mode}")
        if depth > 1 and mode == "focused":
            raise ValueError("Snowball depth above one requires systematic_review or method_lineage mode")
        for name, value in {
            "max_papers": max_papers,
            "max_edges": max_edges,
            "max_provider_operations": max_provider_operations,
            "max_external_queries": max_external_queries,
            "max_frontier": max_frontier,
        }.items():
            if value < 1:
                raise ValueError(f"{name} must be positive")
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
        external_queries = 0
        truncated_reasons: set[str] = set()

        while queue:
            if len(provider_results) >= max_provider_operations:
                truncated_reasons.add("provider_operation_budget")
                break
            if external_queries >= max_external_queries:
                truncated_reasons.add("external_query_budget")
                break
            current, current_id, current_depth = queue.popleft()
            if current_depth >= depth:
                continue
            identifier = _best_identifier(current)
            if not identifier:
                continue
            for connector in self.connectors:
                for direction in directions:
                    if len(provider_results) >= max_provider_operations:
                        truncated_reasons.add("provider_operation_budget")
                        break
                    remaining_queries = max_external_queries - external_queries
                    if remaining_queries <= 0:
                        truncated_reasons.add("external_query_budget")
                        break
                    operation = "references" if direction == "references" else "citations"
                    operation_limit = _graph_result_limit(
                        connector,
                        operation,
                        max_results_per_provider,
                        remaining_queries,
                    )
                    if operation_limit is None:
                        truncated_reasons.add("external_query_budget")
                        continue
                    result = (
                        connector.references_result(identifier, operation_limit)
                        if direction == "references"
                        else connector.citations_result(identifier, operation_limit)
                    )
                    provider_results.append(result)
                    external_queries += result.query_count
                    for record in result.records:
                        if len(edges) >= max_edges:
                            truncated_reasons.add("edge_budget")
                            break
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
                        if target_id not in visited and len(visited) - 1 < max_papers:
                            visited.add(target_id)
                            if len(queue) < max_frontier:
                                queue.append((record, target_id, current_depth + 1))
                            else:
                                truncated_reasons.add("frontier_budget")
                        elif target_id not in visited:
                            truncated_reasons.add("paper_budget")
                    if len(edges) >= max_edges:
                        break
                if (
                    len(provider_results) >= max_provider_operations
                    or external_queries >= max_external_queries
                    or len(edges) >= max_edges
                ):
                    break

        all_papers = merge_paper_records(collected)
        edge_map = {
            (edge.source_paper_id, edge.target_paper_id, edge.relation, edge.provider, edge.depth): edge
            for edge in edges
        }
        all_papers.sort(key=_search_sort_key)
        papers = all_papers
        if len(all_papers) > max_papers:
            papers = all_papers[:max_papers]
            truncated_reasons.add("paper_budget")
        result = _operation_result(
            "snowball",
            provider_results,
            papers,
            observation_count=len(collected),
            metrics_papers=all_papers,
            include_diagnostics=include_diagnostics,
        )
        result["seed_paper_id"] = seed_id
        result["edges"] = [edge.to_dict() for edge in list(edge_map.values())[:max_edges]]
        result["depth"] = depth
        result["mode"] = mode
        result["truncated"] = bool(truncated_reasons)
        result["truncation_reasons"] = sorted(truncated_reasons)
        result["budgets"] = {
            "max_papers": max_papers,
            "max_edges": max_edges,
            "max_provider_operations": max_provider_operations,
            "max_external_queries": max_external_queries,
            "max_frontier": max_frontier,
        }
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
    *,
    observation_count: int = 0,
    metrics_papers: list[dict[str, Any]] | None = None,
    include_diagnostics: bool = False,
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
    compact_papers = [_paper_result(paper, include_diagnostics=include_diagnostics) for paper in papers]
    result = {
        "schema_version": "simflow.literature_result.v1",
        "operation": operation,
        "status": status,
        "papers": compact_papers,
        "providers": _provider_summary(provider_results),
        "errors": [
            {"provider": result.provider, "error": result.error, "retryable": result.retryable}
            for result in errors
        ],
        "metrics": _operation_metrics(
            provider_results,
            metrics_papers if metrics_papers is not None else papers,
            observation_count,
        ),
    }
    if include_diagnostics:
        result["provider_results"] = [
            provider_result.to_dict(include_records=True)
            for provider_result in provider_results
        ]
    return result


def _paper_result(paper: dict[str, Any], *, include_diagnostics: bool) -> dict[str, Any]:
    result = dict(paper)
    observations = list(result.pop("observations", []))
    field_sources = result.pop("field_sources", {})
    conflicts = list(result.pop("conflicts", []))
    sources = sorted({str(item.get("source") or "unknown") for item in observations})
    metadata_state = (result.get("evidence") or {}).get("metadata")
    result["provenance"] = {
        "sources": sources,
        "cross_checked_by": sources if metadata_state == "cross_checked" else [],
        "conflict_fields": sorted({item.get("field") for item in conflicts if item.get("field")}),
    }
    result["local_full_text"] = [
        dict(item["full_text"])
        for item in observations
        if item.get("full_text") and item["full_text"].get("verified")
    ]
    if include_diagnostics:
        result["observations"] = observations
        result["field_sources"] = field_sources
        result["conflicts"] = conflicts
    return result


def _operation_metrics(
    provider_results: list[ProviderResult],
    papers: list[dict[str, Any]],
    observation_count: int,
) -> dict[str, Any]:
    unique_count = len(papers)
    duplicate_count = max(0, observation_count - unique_count)
    cross_checked = sum(
        1 for paper in papers if (paper.get("evidence") or {}).get("metadata") == "cross_checked"
    )
    return {
        "external_query_count": sum(max(0, result.query_count) for result in provider_results),
        "provider_operation_count": len(provider_results),
        "metadata_query_count": sum(
            result.query_count for result in provider_results if result.operation == "metadata"
        ),
        "search_query_count": sum(
            result.query_count for result in provider_results if result.operation == "search"
        ),
        "graph_query_count": sum(
            result.query_count
            for result in provider_results
            if result.operation in {"references", "citations"}
        ),
        "input_observation_count": observation_count,
        "unique_paper_count": unique_count,
        "duplicate_count": duplicate_count,
        "duplicate_rate": duplicate_count / observation_count if observation_count else 0.0,
        "cross_checked_count": cross_checked,
        "cross_checked_ratio": cross_checked / unique_count if unique_count else 0.0,
    }


def _provider_summary(provider_results: list[ProviderResult]) -> list[dict[str, Any]]:
    grouped: dict[str, list[ProviderResult]] = {}
    for result in provider_results:
        grouped.setdefault(result.provider, []).append(result)
    summaries = []
    for provider, results in grouped.items():
        statuses = {item.status for item in results}
        if "success" in statuses and "error" in statuses:
            status = "partial"
        elif "success" in statuses:
            status = "success"
        elif "error" in statuses:
            status = "error"
        elif statuses == {"unsupported"}:
            status = "unsupported"
        else:
            status = "empty"
        summaries.append({
            "provider": provider,
            "status": status,
            "operations": sorted({item.operation for item in results}),
            "query_count": sum(item.query_count for item in results),
            "record_count": sum(len(item.records) for item in results),
        })
    return summaries


def _corpus_verification_sort_key(record: dict[str, Any]) -> tuple[int, int]:
    title = normalize_title(record.get("title"))
    source = _source_key(record.get("source"))
    needs_metadata = not title or source == "local_doi"
    return (0 if needs_metadata else 1, 0 if source == "local_pdf" else 1)


def _paper_for_expected(expected: dict[str, Any], papers: list[dict[str, Any]]) -> dict[str, Any]:
    ranked = sorted(
        papers,
        key=lambda paper: match_records(expected, paper).get("confidence", 0.0),
        reverse=True,
    )
    return ranked[0]


def _graph_result_limit(
    connector: Any,
    operation: str,
    requested: int,
    remaining_queries: int,
) -> int | None:
    provider = str(getattr(connector, "provider_name", ""))
    if provider != "openalex":
        return requested
    if operation == "references":
        if remaining_queries < 1:
            return None
        return max(0, min(requested, remaining_queries - 1))
    if operation == "citations" and remaining_queries < 2:
        return None
    return requested


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
