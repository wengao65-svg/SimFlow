"""OpenAlex literature connector (no API key required).

OpenAlex provides a free, open API for scholarly metadata with a generous
polite pool (no key needed, just set a polite email via SIMFLOW_OPENALEX_EMAIL).
Docs: https://docs.openalex.org/api
"""

import json
import os
import urllib.parse
import urllib.request
from typing import Optional
from urllib.error import HTTPError, URLError

from .base import BaseLiteratureConnector
from mcp.shared.retry import retry_with_backoff, RetryableError
from mcp.shared.cache import TTLCache

OPENALEX_API = "https://api.openalex.org/works"


class OpenAlexConnector(BaseLiteratureConnector):
    """Connector for OpenAlex scholarly metadata search (no key required)."""

    def __init__(self):
        self._cache = TTLCache(max_size=128, ttl_seconds=900)
        self._email = os.environ.get("SIMFLOW_OPENALEX_EMAIL", "")

    def search(self, query: str, max_results: int = 20, **kwargs) -> list:
        """Search OpenAlex for works matching the query."""
        cache_key = "search:{}:{}".format(query, max_results)
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        params = {
            "search": query,
            "per_page": min(max_results, 200),
            "sort": "relevance_score:desc",
        }
        if self._email:
            params["mailto"] = self._email
        url = "{}?{}".format(OPENALEX_API, urllib.parse.urlencode(params))

        success, result = retry_with_backoff(lambda: self._fetch(url))
        if not success:
            return []

        works = self._parse_search_results(result)
        self._cache.set(cache_key, works)
        return works

    def get_metadata(self, doi: str) -> Optional[dict]:
        """Get metadata for a specific DOI via OpenAlex."""
        doi_clean = doi.strip()
        if doi_clean.startswith("https://doi.org/"):
            doi_clean = doi_clean[len("https://doi.org/"):]
        elif doi_clean.startswith("doi.org/"):
            doi_clean = doi_clean[len("doi.org/"):]

        cache_key = "meta:{}".format(doi_clean)
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        url = "https://api.openalex.org/works/doi:{}".format(urllib.parse.quote(doi_clean))
        if self._email:
            url += "?mailto={}".format(urllib.parse.quote(self._email))

        success, result = retry_with_backoff(lambda: self._fetch(url))
        if not success:
            return None

        meta = self._parse_single_work(result)
        if meta:
            self._cache.set(cache_key, meta)
        return meta

    @staticmethod
    def _fetch(url: str) -> str:
        """Fetch URL content."""
        try:
            req = urllib.request.Request(url)
            req.add_header("User-Agent", "SimFlow/0.9.0 (OpenAlex)")
            req.add_header("Accept", "application/json")
            with urllib.request.urlopen(req, timeout=30) as response:
                return response.read().decode("utf-8")
        except HTTPError as e:
            if e.code == 429:
                raise RetryableError("OpenAlex rate limited: HTTP {}".format(e.code)) from e
            raise
        except URLError:
            raise

    def _parse_search_results(self, json_data: str) -> list:
        """Parse OpenAlex search results JSON."""
        try:
            data = json.loads(json_data)
        except json.JSONDecodeError:
            return []

        works = data.get("results", [])
        papers = []
        for work in works:
            paper = self._normalize_work(work)
            if paper:
                papers.append(paper)
        return papers

    def _parse_single_work(self, json_data: str) -> Optional[dict]:
        """Parse a single OpenAlex work JSON."""
        try:
            work = json.loads(json_data)
        except json.JSONDecodeError:
            return None
        return self._normalize_work(work)

    @staticmethod
    def _normalize_work(work: dict) -> Optional[dict]:
        """Normalize an OpenAlex work record to SimFlow's paper dict format."""
        if not isinstance(work, dict) or not work.get("id"):
            return None

        # DOI
        doi = work.get("doi") or ""
        if doi and doi.startswith("https://doi.org/"):
            doi = doi[len("https://doi.org/"):]

        # Title
        title = work.get("title") or work.get("display_name") or ""

        # Authors
        authorships = work.get("authorships", [])
        authors = []
        for authorship in authorships:
            author = authorship.get("author", {})
            name = author.get("display_name") or ""
            if name:
                authors.append(name)

        # Abstract (OpenAlex stores it as inverted index)
        abstract = ""
        abstract_index = work.get("abstract_inverted_index")
        if isinstance(abstract_index, dict):
            word_positions = []
            for word, positions in abstract_index.items():
                for pos in positions:
                    word_positions.append((pos, word))
            word_positions.sort()
            abstract = " ".join(word for _, word in word_positions)

        # Year
        year = work.get("publication_year") or work.get("publication_date", "")[:4]

        # Venue
        venue_obj = work.get("primary_location", {}).get("source", {}) if isinstance(work.get("primary_location"), dict) else {}
        venue = venue_obj.get("display_name", "") if isinstance(venue_obj, dict) else ""

        # URL
        url = work.get("id", "")

        return {
            "doi": doi,
            "title": title,
            "authors": authors,
            "journal": venue,
            "year": year,
            "abstract": abstract,
            "source": "OpenAlex",
            "url": url,
        }
