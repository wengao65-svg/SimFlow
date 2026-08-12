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
from ..cache import TTLCache
from ..retry import RetryableError, retry_with_backoff

OPENALEX_API = "https://api.openalex.org/works"


class OpenAlexConnector(BaseLiteratureConnector):
    """Connector for OpenAlex scholarly metadata search (no key required)."""

    provider_name = "openalex"

    def __init__(self):
        self._cache = TTLCache(max_size=128, ttl_seconds=900)
        self._email = os.environ.get("SIMFLOW_OPENALEX_EMAIL", "")
        self._api_key = os.environ.get("OPENALEX_API_KEY", "")
        self._last_error = None

    def search(self, query: str, max_results: int = 20, **kwargs) -> list:
        """Search OpenAlex for works matching the query."""
        self._set_error(None)
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
        if self._api_key:
            params["api_key"] = self._api_key
        url = "{}?{}".format(OPENALEX_API, urllib.parse.urlencode(params))

        success, result = retry_with_backoff(lambda: self._fetch(url))
        if not success:
            self._set_error(result)
            return []

        works = self._parse_search_results(result)
        self._cache.set(cache_key, works)
        return works

    def get_metadata(self, doi: str) -> Optional[dict]:
        """Get metadata for a specific DOI via OpenAlex."""
        self._set_error(None)
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
            separator = "&" if "?" in url else "?"
            url += "{}mailto={}".format(separator, urllib.parse.quote(self._email))
        if self._api_key:
            separator = "&" if "?" in url else "?"
            url += "{}api_key={}".format(separator, urllib.parse.quote(self._api_key))

        success, result = retry_with_backoff(lambda: self._fetch(url))
        if not success:
            self._set_error(result)
            return None

        meta = self._parse_single_work(result)
        if meta:
            self._cache.set(cache_key, meta)
        return meta

    def references_result(self, identifier: str, max_results: int = 20):
        """Return referenced works by following the seed's OpenAlex graph IDs."""
        from ..models import ProviderResult

        seed = self._get_work(identifier)
        if seed is None:
            error = self.last_error
            return ProviderResult(
                provider=self.provider_name,
                operation="references",
                status="error" if error else "empty",
                error=str(error or ""),
            )
        records = []
        for work_id in list(seed.get("referenced_works") or [])[:max_results]:
            work = self._get_work(work_id)
            if work:
                normalized = self._normalize_work(work)
                if normalized:
                    records.append(normalized)
        return ProviderResult(
            provider=self.provider_name,
            operation="references",
            status="success" if records else "empty",
            records=records,
        )

    def citations_result(self, identifier: str, max_results: int = 20):
        """Return works citing the seed using OpenAlex's cites filter."""
        from ..models import ProviderResult

        seed = self._get_work(identifier)
        if seed is None:
            error = self.last_error
            return ProviderResult(
                provider=self.provider_name,
                operation="citations",
                status="error" if error else "empty",
                error=str(error or ""),
            )
        work_id = str(seed.get("id") or "").rsplit("/", 1)[-1]
        params = {"filter": f"cites:{work_id}", "per_page": min(max_results, 200)}
        if self._email:
            params["mailto"] = self._email
        if self._api_key:
            params["api_key"] = self._api_key
        url = "{}?{}".format(OPENALEX_API, urllib.parse.urlencode(params))
        self._set_error(None)
        success, result = retry_with_backoff(lambda: self._fetch(url))
        if not success:
            self._set_error(result)
            return ProviderResult(
                provider=self.provider_name,
                operation="citations",
                status="error",
                error=str(result),
            )
        records = self._parse_search_results(result)
        return ProviderResult(
            provider=self.provider_name,
            operation="citations",
            status="success" if records else "empty",
            records=records,
        )

    def _get_work(self, identifier: str) -> Optional[dict]:
        """Fetch raw work JSON by DOI, OpenAlex ID, or URL."""
        self._set_error(None)
        raw = str(identifier or "").strip()
        if raw.startswith("10.") or "doi.org/" in raw:
            doi = raw.rsplit("doi.org/", 1)[-1]
            target = f"doi:{urllib.parse.quote(doi, safe='')}"
        else:
            target = raw.rsplit("/", 1)[-1]
        url = f"{OPENALEX_API}/{target}"
        if self._email:
            url += "?mailto={}".format(urllib.parse.quote(self._email))
        if self._api_key:
            separator = "&" if "?" in url else "?"
            url += "{}api_key={}".format(separator, urllib.parse.quote(self._api_key))
        success, result = retry_with_backoff(lambda: self._fetch(url))
        if not success:
            self._set_error(result)
            return None
        try:
            return json.loads(result)
        except json.JSONDecodeError as error:
            self._set_error(error)
            return None

    @staticmethod
    def _fetch(url: str) -> str:
        """Fetch URL content."""
        try:
            req = urllib.request.Request(url)
            req.add_header("User-Agent", "SimFlow/1.2.0-dev.0 (OpenAlex)")
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

        openalex_id = str(work.get("id") or "").rsplit("/", 1)[-1]
        ids = work.get("ids") or {}
        identifiers = {"openalex": openalex_id}
        if doi:
            identifiers["doi"] = doi
        for source_key, target_key in (("pmid", "pmid"), ("pmcid", "pmcid")):
            value = str(ids.get(source_key) or "")
            if value:
                identifiers[target_key] = value.rsplit("/", 1)[-1]

        locations = []
        for location in work.get("locations") or []:
            pdf_url = location.get("pdf_url") or ""
            landing_url = location.get("landing_page_url") or ""
            if not pdf_url and not landing_url:
                continue
            source = location.get("source") or {}
            locations.append({
                "pdf_url": pdf_url,
                "landing_page_url": landing_url,
                "is_oa": bool(location.get("is_oa")),
                "license": location.get("license") or "",
                "version": location.get("version") or "",
                "host_type": source.get("host_organization_name") or source.get("display_name") or "",
            })

        return {
            "id": openalex_id,
            "doi": doi,
            "title": title,
            "authors": authors,
            "journal": venue,
            "year": year,
            "abstract": abstract,
            "citation_count": work.get("cited_by_count"),
            "identifiers": identifiers,
            "open_access_locations": locations,
            "source": "OpenAlex",
            "url": work.get("id", ""),
        }
