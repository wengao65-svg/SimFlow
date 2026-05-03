"""Crossref literature connector."""

import json
import urllib.parse
import urllib.request
from typing import Optional

from .base import BaseLiteratureConnector

CROSSREF_API = "https://api.crossref.org"


class CrossrefConnector(BaseLiteratureConnector):
    """Connector for Crossref DOI metadata."""

    def search(self, query: str, max_results: int = 20, **kwargs) -> list:
        """Search Crossref for works."""
        params = urllib.parse.urlencode({
            "query": query,
            "rows": max_results,
            "select": "DOI,title,author,published-print,abstract,container-title",
        })
        url = "{}/works?{}".format(CROSSREF_API, params)

        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "SimFlow/0.5.0 (mailto:simflow@example.com)"
            })
            with urllib.request.urlopen(req, timeout=30) as response:
                data = json.loads(response.read().decode("utf-8"))
        except Exception:
            return []

        return self._parse_results(data)

    def get_metadata(self, doi: str) -> Optional[dict]:
        """Get metadata for a specific DOI."""
        doi = doi.strip()
        if not doi.startswith("10."):
            return None

        url = "{}/works/{}".format(CROSSREF_API, urllib.parse.quote(doi, safe=""))

        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "SimFlow/0.5.0 (mailto:simflow@example.com)"
            })
            with urllib.request.urlopen(req, timeout=30) as response:
                data = json.loads(response.read().decode("utf-8"))
        except Exception:
            return None

        item = data.get("message", {})
        return self._format_item(item) if item else None

    def _parse_results(self, data: dict) -> list:
        """Parse Crossref search results."""
        items = data.get("message", {}).get("items", [])
        return [self._format_item(item) for item in items]

    def _format_item(self, item: dict) -> dict:
        """Format a Crossref item to standard format."""
        title_parts = item.get("title", [])
        title = title_parts[0] if title_parts else ""

        authors = []
        for author in item.get("author", []):
            name = "{} {}".format(author.get("given", ""), author.get("family", "")).strip()
            if name:
                authors.append(name)

        pub_date = item.get("published-print", item.get("published-online", {}))
        date_parts = pub_date.get("date-parts", [[]])
        year = date_parts[0][0] if date_parts and date_parts[0] else None

        return {
            "id": item.get("DOI", ""),
            "title": title,
            "authors": authors,
            "abstract": item.get("abstract", ""),
            "year": year,
            "journal": item.get("container-title", [""])[0] if item.get("container-title") else "",
            "doi": item.get("DOI", ""),
            "source": "Crossref",
            "url": "https://doi.org/{}".format(item.get("DOI", "")),
        }
