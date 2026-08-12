"""arXiv literature connector."""

import re
import time
import urllib.parse
import urllib.request
from typing import Optional
from urllib.error import HTTPError, URLError
from xml.etree import ElementTree

from .base import BaseLiteratureConnector
from ..identity import normalize_arxiv_id, normalize_doi
from ..cache import TTLCache
from ..retry import RetryableError, retry_with_backoff

ARXIV_API = "https://export.arxiv.org/api/query"


class ArxivConnector(BaseLiteratureConnector):
    """Connector for arXiv paper search."""

    provider_name = "arxiv"

    def __init__(self):
        self._cache = TTLCache(max_size=128, ttl_seconds=900)
        self._last_error = None
        self._last_request_at = 0.0

    def search(self, query: str, max_results: int = 20, **kwargs) -> list:
        """Search arXiv for papers."""
        self._set_error(None)
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
            self._set_error(result)
            return []

        results = self._parse_results(result)
        self._cache.set(cache_key, results)
        return results

    def get_metadata(self, arxiv_id: str) -> Optional[dict]:
        """Get metadata for a specific arXiv paper."""
        self._set_error(None)
        arxiv_id = normalize_arxiv_id(arxiv_id, keep_version=True)
        if not arxiv_id:
            return None
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
            self._set_error(result)
            return None

        results = self._parse_results(result)
        meta = results[0] if results else None
        if meta:
            self._cache.set(cache_key, meta)
        return meta

    def _fetch(self, url: str) -> str:
        """Fetch URL content with structured error handling."""
        elapsed = time.monotonic() - self._last_request_at
        if elapsed < 3.0:
            time.sleep(3.0 - elapsed)
        try:
            req = urllib.request.Request(url)
            req.add_header("User-Agent", "SimFlow/1.2.0-dev.0")
            with urllib.request.urlopen(req, timeout=30) as response:
                return response.read().decode("utf-8")
        except HTTPError as e:
            if e.code == 429:
                raise RetryableError("arXiv rate limited: HTTP {}".format(e.code)) from e
            raise
        except URLError as e:
            raise
        finally:
            self._last_request_at = time.monotonic()

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
            arxiv_version = ""
            if id_elem is not None and id_elem.text:
                raw_id = id_elem.text.strip()
                arxiv_id = normalize_arxiv_id(raw_id)
                arxiv_version = normalize_arxiv_id(raw_id, keep_version=True)

            doi = ""
            journal_ref = ""
            pdf_url = ""
            for child in entry:
                tag = child.tag.rsplit("}", 1)[-1]
                if tag == "doi":
                    doi = normalize_doi(child.text)
                elif tag == "journal_ref":
                    journal_ref = child.text or ""
                elif tag == "link" and child.get("title") == "pdf":
                    pdf_url = child.get("href") or ""

            identifiers = {"arxiv": arxiv_id}
            if doi:
                identifiers["doi"] = doi
            locations = [{
                "pdf_url": pdf_url or (f"https://arxiv.org/pdf/{arxiv_version or arxiv_id}" if arxiv_id else ""),
                "landing_page_url": f"https://arxiv.org/abs/{arxiv_version or arxiv_id}" if arxiv_id else "",
                "is_oa": True,
                "license": "",
                "version": arxiv_version or arxiv_id,
                "host_type": "arXiv",
            }] if arxiv_id else []

            papers.append({
                "id": arxiv_id,
                "arxiv_id": arxiv_id,
                "arxiv_version": arxiv_version,
                "doi": doi,
                "title": title.text.strip().replace("\n", " ") if title is not None else "",
                "authors": [a.text for a in authors if a.text],
                "abstract": summary.text.strip() if summary is not None else "",
                "published": published.text if published is not None else "",
                "year": int(published.text[:4]) if published is not None and published.text else None,
                "journal": journal_ref,
                "identifiers": identifiers,
                "open_access_locations": locations,
                "source": "arXiv",
                "url": "https://arxiv.org/abs/{}".format(arxiv_version or arxiv_id) if arxiv_id else "",
            })

        return papers
