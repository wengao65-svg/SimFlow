"""Semantic Scholar literature connector."""

import json
import os
import urllib.parse
import urllib.request
from typing import Optional

from .base import BaseLiteratureConnector

S2_API = "https://api.semanticscholar.org/graph/v1"


class SemanticScholarConnector(BaseLiteratureConnector):
    """Connector for Semantic Scholar paper search."""

    def __init__(self):
        self.api_key = os.environ.get("S2_API_KEY")

    def search(self, query: str, max_results: int = 20, **kwargs) -> list:
        """Search Semantic Scholar for papers."""
        params = urllib.parse.urlencode({
            "query": query,
            "limit": max_results,
            "fields": "title,authors,abstract,year,externalIds,url,citationCount",
        })
        url = "{}/paper/search?{}".format(S2_API, params)

        try:
            req = urllib.request.Request(url)
            if self.api_key:
                req.add_header("x-api-key", self.api_key)
            with urllib.request.urlopen(req, timeout=30) as response:
                data = json.loads(response.read().decode("utf-8"))
        except Exception:
            return []

        return self._parse_results(data)

    def get_metadata(self, paper_id: str) -> Optional[dict]:
        """Get metadata for a specific paper by Semantic Scholar ID or DOI."""
        # Handle DOI input
        if paper_id.startswith("10."):
            paper_id = "DOI:{}".format(paper_id)

        url = "{}/paper/{}?fields=title,authors,abstract,year,externalIds,url,citationCount,venue".format(
            S2_API, urllib.parse.quote(paper_id, safe="")
        )

        try:
            req = urllib.request.Request(url)
            if self.api_key:
                req.add_header("x-api-key", self.api_key)
            with urllib.request.urlopen(req, timeout=30) as response:
                data = json.loads(response.read().decode("utf-8"))
        except Exception:
            return None

        return self._format_paper(data) if data and data.get("paperId") else None

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
