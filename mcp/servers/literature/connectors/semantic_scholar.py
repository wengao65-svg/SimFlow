"""Semantic Scholar literature connector."""

import json
import os
import urllib.parse
import urllib.request
from typing import Optional
from urllib.error import HTTPError, URLError

from .base import BaseLiteratureConnector
from mcp.shared.retry import retry_with_backoff, RetryableError
from mcp.shared.cache import TTLCache

S2_API = "https://api.semanticscholar.org/graph/v1"


class SemanticScholarConnector(BaseLiteratureConnector):
    """Connector for Semantic Scholar paper search."""

    def __init__(self):
        self.api_key = os.environ.get("S2_API_KEY")
        self._cache = TTLCache(max_size=128, ttl_seconds=900)

    def search(self, query: str, max_results: int = 20, **kwargs) -> list:
        """Search Semantic Scholar for papers."""
        cache_key = "search:{}:{}".format(query, max_results)
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        params = urllib.parse.urlencode({
            "query": query,
            "limit": max_results,
            "fields": "title,authors,abstract,year,externalIds,url,citationCount",
        })
        url = "{}/paper/search?{}".format(S2_API, params)

        success, result = retry_with_backoff(
            lambda: self._fetch_json(url)
        )
        if not success:
            return []

        results = self._parse_results(result)
        self._cache.set(cache_key, results)
        return results

    def get_metadata(self, paper_id: str) -> Optional[dict]:
        """Get metadata for a specific paper by Semantic Scholar ID or DOI."""
        if paper_id.startswith("10."):
            paper_id = "DOI:{}".format(paper_id)

        cache_key = "meta:{}".format(paper_id)
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        url = "{}/paper/{}?fields=title,authors,abstract,year,externalIds,url,citationCount,venue".format(
            S2_API, urllib.parse.quote(paper_id, safe="")
        )

        success, result = retry_with_backoff(
            lambda: self._fetch_json(url)
        )
        if not success:
            return None

        meta = self._format_paper(result) if result and result.get("paperId") else None
        if meta:
            self._cache.set(cache_key, meta)
        return meta

    def _fetch_json(self, url: str) -> dict:
        """Fetch JSON from URL with structured error handling."""
        try:
            req = urllib.request.Request(url)
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
        doi = external_ids.get("DOI", "") if external_ids else ""

        return {
            "id": paper.get("paperId", ""),
            "title": paper.get("title", ""),
            "authors": [a.get("name", "") for a in paper.get("authors", [])],
            "abstract": paper.get("abstract", "") or "",
            "year": paper.get("year"),
            "doi": doi,
            "citation_count": paper.get("citationCount"),
            "venue": paper.get("venue", ""),
            "source": "Semantic Scholar",
            "url": paper.get("url", ""),
        }
