"""Crystallography Open Database (COD) connector."""

import json
import urllib.parse
import urllib.request
from typing import Optional
from urllib.error import HTTPError, URLError

from .base import BaseStructureConnector
from mcp.shared.retry import retry_with_backoff, RetryableError
from mcp.shared.cache import TTLCache

COD_API = "https://www.crystallography.net/cod"


class CODConnector(BaseStructureConnector):
    """Connector for Crystallography Open Database."""

    def __init__(self):
        self._cache = TTLCache(max_size=128, ttl_seconds=900)

    def search(self, formula: str, **kwargs) -> list:
        """Search COD for crystal structures by formula."""
        cache_key = "search:{}".format(formula)
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        max_results = kwargs.get("max_results", 20)
        params = urllib.parse.urlencode({
            "formula": formula,
            "format": "json",
            "limit": max_results,
        })
        url = "{}/search?{}".format(COD_API, params)

        success, result = retry_with_backoff(
            lambda: self._fetch_json(url)
        )
        if not success:
            return []

        results = self._parse_results(result)
        self._cache.set(cache_key, results)
        return results

    def get_structure(self, cod_id: str) -> Optional[dict]:
        """Get structure data by COD ID."""
        cache_key = "struct:{}".format(cod_id)
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        url = "{}/{}.json".format(COD_API, cod_id.strip())

        success, result = retry_with_backoff(
            lambda: self._fetch_json(url)
        )
        if not success:
            return None

        if result and isinstance(result, list) and len(result) > 0:
            meta = self._format_entry(result[0])
        elif result and isinstance(result, dict):
            meta = self._format_entry(result)
        else:
            return None

        self._cache.set(cache_key, meta)
        return meta

    @staticmethod
    def _fetch_json(url: str):
        """Fetch JSON from URL with structured error handling."""
        try:
            req = urllib.request.Request(url)
            req.add_header("User-Agent", "SimFlow/0.5.0")
            with urllib.request.urlopen(req, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as e:
            if e.code == 429:
                raise RetryableError("COD rate limited: HTTP {}".format(e.code)) from e
            raise
        except URLError as e:
            raise

    def _parse_results(self, data: list) -> list:
        """Parse COD search results."""
        if not isinstance(data, list):
            return []
        return [self._format_entry(entry) for entry in data[:50]]

    def _format_entry(self, entry: dict) -> dict:
        """Format a COD entry to standard format."""
        cell = entry.get("cell", {})
        return {
            "cod_id": str(entry.get("cod_id", entry.get("id", ""))),
            "formula": entry.get("formula", entry.get("chemical_formula_sum", "")),
            "space_group": entry.get("space_group", entry.get("_symmetry_space_group_name_H-M", "")),
            "lattice_parameters": {
                "a": cell.get("a"),
                "b": cell.get("b"),
                "c": cell.get("c"),
                "alpha": cell.get("alpha"),
                "beta": cell.get("beta"),
                "gamma": cell.get("gamma"),
            } if cell else {},
            "num_atoms": entry.get("natom"),
            "authors": entry.get("authors", ""),
            "journal": entry.get("journal", entry.get("_journal_name_full", "")),
            "year": entry.get("year", entry.get("_journal_year")),
            "source": "COD",
        }
