"""Semantic Scholar literature connector."""

import json
import os
import urllib.parse
import urllib.request
from typing import Optional
from urllib.error import HTTPError, URLError

from .base import BaseLiteratureConnector
from ..identity import normalize_arxiv_id, normalize_doi
from ..cache import TTLCache
from ..retry import RetryableError, retry_with_backoff

S2_API = "https://api.semanticscholar.org/graph/v1"


class SemanticScholarConnector(BaseLiteratureConnector):
    """Connector for Semantic Scholar paper search."""

    provider_name = "semantic_scholar"

    def __init__(self):
        self.api_key = os.environ.get("S2_API_KEY")
        self._cache = TTLCache(max_size=128, ttl_seconds=900)
        self._last_error = None

    def search(self, query: str, max_results: int = 20, **kwargs) -> list:
        """Search Semantic Scholar for papers."""
        self._set_error(None)
        cache_key = "search:{}:{}".format(query, max_results)
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        params = urllib.parse.urlencode({
            "query": query,
            "limit": max_results,
            "fields": "title,authors,abstract,year,externalIds,url,citationCount,venue,openAccessPdf",
        })
        url = "{}/paper/search?{}".format(S2_API, params)

        success, result = retry_with_backoff(
            lambda: self._fetch_json(url)
        )
        if not success:
            self._set_error(result)
            return []

        results = self._parse_results(result)
        self._cache.set(cache_key, results)
        return results

    def get_metadata(self, paper_id: str) -> Optional[dict]:
        """Get metadata for a specific paper by Semantic Scholar ID or DOI."""
        self._set_error(None)
        paper_id = self._paper_id(paper_id)

        cache_key = "meta:{}".format(paper_id)
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        url = "{}/paper/{}?fields=title,authors,abstract,year,externalIds,url,citationCount,venue,openAccessPdf".format(
            S2_API, urllib.parse.quote(paper_id, safe="")
        )

        success, result = retry_with_backoff(
            lambda: self._fetch_json(url)
        )
        if not success:
            self._set_error(result)
            return None

        meta = self._format_paper(result) if result and result.get("paperId") else None
        if meta:
            self._cache.set(cache_key, meta)
        return meta

    def references_result(self, identifier: str, max_results: int = 20):
        return self._graph_result(identifier, "references", "citedPaper", max_results)

    def citations_result(self, identifier: str, max_results: int = 20):
        return self._graph_result(identifier, "citations", "citingPaper", max_results)

    def _graph_result(self, identifier: str, operation: str, nested_key: str, max_results: int):
        from ..models import ProviderResult

        paper_id = self._paper_id(identifier)
        fields = "title,authors,abstract,year,externalIds,url,citationCount,venue,openAccessPdf"
        url = f"{S2_API}/paper/{urllib.parse.quote(paper_id, safe='')}/{operation}?limit={max_results}&fields={fields}"
        self._set_error(None)
        success, result = retry_with_backoff(lambda: self._fetch_json(url))
        if not success:
            self._set_error(result)
            return ProviderResult(
                provider=self.provider_name,
                operation=operation,
                status="error",
                error=str(result),
            )
        records = []
        for item in result.get("data", []):
            paper = item.get(nested_key) or {}
            if paper.get("paperId"):
                records.append(self._format_paper(paper))
        return ProviderResult(
            provider=self.provider_name,
            operation=operation,
            status="success" if records else "empty",
            records=records,
        )

    @staticmethod
    def _paper_id(identifier: str) -> str:
        raw = str(identifier or "").strip()
        doi = normalize_doi(raw)
        if doi:
            return f"DOI:{doi}"
        arxiv_id = normalize_arxiv_id(raw, keep_version=True)
        if arxiv_id:
            return f"ARXIV:{arxiv_id}"
        return raw

    def _fetch_json(self, url: str) -> dict:
        """Fetch JSON from URL with structured error handling."""
        try:
            req = urllib.request.Request(url)
            req.add_header("User-Agent", "SimFlow/1.2.0-dev.0")
            if self.api_key:
                req.add_header("x-api-key", self.api_key)
            with urllib.request.urlopen(req, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as e:
            if e.code == 429:
                raise RetryableError("Semantic Scholar rate limited: HTTP {}".format(e.code)) from e
            raise
        except URLError as e:
            raise

    def _parse_results(self, data: dict) -> list:
        """Parse Semantic Scholar search results."""
        papers = data.get("data", [])
        return [self._format_paper(p) for p in papers]

    def _format_paper(self, paper: dict) -> dict:
        """Format a Semantic Scholar paper to standard format."""
        external_ids = paper.get("externalIds", {})
        doi = normalize_doi(external_ids.get("DOI", "")) if external_ids else ""
        identifiers = {"semantic_scholar": paper.get("paperId", "")}
        if doi:
            identifiers["doi"] = doi
        arxiv_id = normalize_arxiv_id(external_ids.get("ArXiv", "")) if external_ids else ""
        if arxiv_id:
            identifiers["arxiv"] = arxiv_id
        pubmed_id = str(external_ids.get("PubMed", "") or "").strip() if external_ids else ""
        if pubmed_id:
            identifiers["pmid"] = pubmed_id
        oa = paper.get("openAccessPdf") or {}
        locations = []
        if oa.get("url"):
            locations.append({
                "pdf_url": oa.get("url"),
                "landing_page_url": "",
                "is_oa": True,
                "license": oa.get("license") or "",
                "version": "",
                "host_type": "Semantic Scholar",
            })

        return {
            "id": paper.get("paperId", ""),
            "title": paper.get("title", ""),
            "authors": [a.get("name", "") for a in paper.get("authors", [])],
            "abstract": paper.get("abstract", "") or "",
            "year": paper.get("year"),
            "doi": doi,
            "citation_count": paper.get("citationCount"),
            "venue": paper.get("venue", ""),
            "identifiers": identifiers,
            "open_access_locations": locations,
            "source": "Semantic Scholar",
            "url": paper.get("url", ""),
        }
