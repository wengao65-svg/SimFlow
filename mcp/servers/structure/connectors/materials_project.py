"""Materials Project structure connector."""

import json
import os
import urllib.parse
import urllib.request
from typing import Optional

from .base import BaseStructureConnector

MP_API = "https://api.materialsproject.org"


class MaterialsProjectConnector(BaseStructureConnector):
    """Connector for Materials Project crystal structure database."""

    def __init__(self):
        self.api_key = os.environ.get("MP_API_KEY")

    def search(self, formula: str, **kwargs) -> list:
        """Search Materials Project for structures by formula."""
        if not self.api_key:
            return []

        params = {
            "formula": formula,
            "fields": "material_id,formula_pretty,structure,space_group,symmetry",
        }
        url = "{}/materials/xas/?{}".format(MP_API, urllib.parse.urlencode(params))

        try:
            req = urllib.request.Request(url)
            req.add_header("X-API-KEY", self.api_key)
            with urllib.request.urlopen(req, timeout=30) as response:
                data = json.loads(response.read().decode("utf-8"))
        except Exception:
            return []

        return self._parse_results(data)

    def get_structure(self, material_id: str) -> Optional[dict]:
        """Get structure data by Materials Project ID."""
        if not self.api_key:
            return None

        url = "{}/materials/{}/".format(MP_API, urllib.parse.quote(material_id, safe=""))

        try:
            req = urllib.request.Request(url)
            req.add_header("X-API-KEY", self.api_key)
            with urllib.request.urlopen(req, timeout=30) as response:
                data = json.loads(response.read().decode("utf-8"))
        except Exception:
            return None

        if data and "data" in data and data["data"]:
            return self._format_material(data["data"][0])
        return None

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
