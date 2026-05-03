"""arXiv literature connector."""

import re
import urllib.parse
import urllib.request
from typing import Optional
from urllib.error import HTTPError, URLError
from xml.etree import ElementTree

from .base import BaseLiteratureConnector
from mcp.shared.retry import retry_with_backoff, RetryableError
from mcp.shared.cache import TTLCache

ARXIV_API = "https://export.arxiv.org/api/query"


class ArxivConnector(BaseLiteratureConnector):
    """Connector for arXiv paper search."""

    def __init__(self):
        self._cache = TTLCache(max_size=128, ttl_seconds=900)

    def search(self, query: str, max_results: int = 20, **kwargs) -> list:
        """Search arXiv for papers."""
        cache_key = "search:{}:{}".format(query, max_results)
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        params = urllib.parse.urlencode({
            "search_query": "all:{}".format(query),
            "start": 0,
            "max_results": max_results,
            "sortBy": "relevance",
            "sortOrder": "descending",
        })
        url = "{}?{}".format(ARXIV_API, params)

        success, result = retry_with_backoff(
            lambda: self._fetch(url)
        )
        if not success:
            return []

        results = self._parse_results(result)
        self._cache.set(cache_key, results)
        return results

    def get_metadata(self, arxiv_id: str) -> Optional[dict]:
        """Get metadata for a specific arXiv paper."""
        arxiv_id = arxiv_id.replace("arXiv:", "").strip()
        cache_key = "meta:{}".format(arxiv_id)
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        params = urllib.parse.urlencode({
            "id_list": arxiv_id,
            "max_results": 1,
        })
        url = "{}?{}".format(ARXIV_API, params)

        success, result = retry_with_backoff(
            lambda: self._fetch(url)
        )
        if not success:
            return None

        results = self._parse_results(result)
        meta = results[0] if results else None
        if meta:
            self._cache.set(cache_key, meta)
        return meta

    @staticmethod
    def _fetch(url: str) -> str:
        """Fetch URL content with structured error handling."""
        try:
            req = urllib.request.Request(url)
            req.add_header("User-Agent", "SimFlow/0.5.0")
            with urllib.request.urlopen(req, timeout=30) as response:
                return response.read().decode("utf-8")
        except HTTPError as e:
            if e.code == 429:
                raise RetryableError("arXiv rate limited: HTTP {}".format(e.code)) from e
            raise
        except URLError as e:
            raise

    def _parse_results(self, xml_data: str) -> list:
        """Parse arXiv Atom XML response."""
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        try:
            root = ElementTree.fromstring(xml_data)
        except ElementTree.ParseError:
            return []

        papers = []
        for entry in root.findall("atom:entry", ns):
            title = entry.find("atom:title", ns)
            summary = entry.find("atom:summary", ns)
            published = entry.find("atom:published", ns)
            authors = entry.findall("atom:author/atom:name", ns)

            id_elem = entry.find("atom:id", ns)
            arxiv_id = ""
            if id_elem is not None and id_elem.text:
                match = re.search(r"(\d+\.\d+)", id_elem.text)
                if match:
                    arxiv_id = match.group(1)

            papers.append({
                "id": arxiv_id,
                "title": title.text.strip().replace("\n", " ") if title is not None else "",
                "authors": [a.text for a in authors if a.text],
                "abstract": summary.text.strip() if summary is not None else "",
                "published": published.text if published is not None else "",
                "source": "arXiv",
                "url": "https://arxiv.org/abs/{}".format(arxiv_id) if arxiv_id else "",
            })

        return papers
