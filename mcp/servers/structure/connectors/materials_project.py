"""Materials Project structure connector."""

import json
import os
import urllib.parse
import urllib.request
from typing import Optional
from urllib.error import HTTPError, URLError

from .base import BaseStructureConnector
from mcp.shared.retry import retry_with_backoff, RetryableError
from mcp.shared.cache import TTLCache

MP_API = "https://api.materialsproject.org"


class MaterialsProjectConnector(BaseStructureConnector):
    """Connector for Materials Project crystal structure database."""

    def __init__(self):
        self.api_key = os.environ.get("MP_API_KEY")
        self._cache = TTLCache(max_size=128, ttl_seconds=900)

    def search(self, formula: str, **kwargs) -> list:
        """Search Materials Project for structures by formula."""
        if not self.api_key:
            return []

        cache_key = "search:{}".format(formula)
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        params = {
            "formula": formula,
            "fields": "material_id,formula_pretty,structure,space_group,symmetry",
        }
        url = "{}/materials/xas/?{}".format(MP_API, urllib.parse.urlencode(params))

        success, result = retry_with_backoff(
            lambda: self._fetch_json(url)
        )
        if not success:
            return []

        results = self._parse_results(result)
        self._cache.set(cache_key, results)
        return results

    def get_structure(self, material_id: str) -> Optional[dict]:
        """Get structure data by Materials Project ID."""
        if not self.api_key:
            return None

        cache_key = "struct:{}".format(material_id)
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        url = "{}/materials/{}/".format(MP_API, urllib.parse.quote(material_id, safe=""))

        success, result = retry_with_backoff(
            lambda: self._fetch_json(url)
        )
        if not success:
            return None

        if result and "data" in result and result["data"]:
            meta = self._format_material(result["data"][0])
            self._cache.set(cache_key, meta)
            return meta
        return None

    def _fetch_json(self, url: str) -> dict:
        """Fetch JSON from URL with structured error handling."""
        try:
            req = urllib.request.Request(url)
            req.add_header("X-API-KEY", self.api_key)
            with urllib.request.urlopen(req, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as e:
            if e.code == 429:
                raise RetryableError("Materials Project rate limited: HTTP {}".format(e.code)) from e
            raise
        except URLError as e:
            raise

    def _parse_results(self, data: dict) -> list:
        """Parse Materials Project search results."""
        items = data.get("data", [])
        return [self._format_material(item) for item in items]

    def _format_material(self, item: dict) -> dict:
        """Format a Materials Project entry to standard format."""
        structure = item.get("structure", {})
        lattice = structure.get("lattice", {}) if structure else {}

        return {
            "material_id": item.get("material_id", ""),
            "formula": item.get("formula_pretty", ""),
            "space_group": item.get("space_group", {}).get("symbol", ""),
            "lattice_parameters": {
                "a": lattice.get("a"),
                "b": lattice.get("b"),
                "c": lattice.get("c"),
                "alpha": lattice.get("alpha"),
                "beta": lattice.get("beta"),
                "gamma": lattice.get("gamma"),
            } if lattice else {},
            "num_sites": structure.get("nsites") if structure else None,
            "source": "Materials Project",
        }
