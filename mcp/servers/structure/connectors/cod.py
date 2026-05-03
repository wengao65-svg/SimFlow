"""Crystallography Open Database (COD) connector."""

import json
import urllib.parse
import urllib.request
from typing import Optional

from .base import BaseStructureConnector

COD_API = "https://www.crystallography.net/cod"


class CODConnector(BaseStructureConnector):
    """Connector for Crystallography Open Database."""

    def search(self, formula: str, **kwargs) -> list:
        """Search COD for crystal structures by formula."""
        max_results = kwargs.get("max_results", 20)
        params = urllib.parse.urlencode({
            "formula": formula,
            "format": "json",
            "limit": max_results,
        })
        url = "{}/search?{}".format(COD_API, params)

        try:
            req = urllib.request.Request(url)
            req.add_header("User-Agent", "SimFlow/0.5.0")
            with urllib.request.urlopen(req, timeout=30) as response:
                data = json.loads(response.read().decode("utf-8"))
        except Exception:
            return []

        return self._parse_results(data)

    def get_structure(self, cod_id: str) -> Optional[dict]:
        """Get structure data by COD ID."""
        url = "{}/{}.json".format(COD_API, cod_id.strip())

        try:
            req = urllib.request.Request(url)
            req.add_header("User-Agent", "SimFlow/0.5.0")
            with urllib.request.urlopen(req, timeout=30) as response:
                data = json.loads(response.read().decode("utf-8"))
        except Exception:
            return None

        if data and isinstance(data, list) and len(data) > 0:
            return self._format_entry(data[0])
        elif data and isinstance(data, dict):
            return self._format_entry(data)
        return None

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
