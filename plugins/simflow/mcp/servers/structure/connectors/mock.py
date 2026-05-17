"""Mock crystal structure connector with preset data."""

from typing import Optional
from .base import BaseStructureConnector


MOCK_STRUCTURES = [
    {
        "material_id": "mp-149",
        "formula": "Si",
        "structure_type": "diamond",
        "space_group": "Fd-3m",
        "lattice_parameters": {"a": 5.431, "b": 5.431, "c": 5.431, "alpha": 90, "beta": 90, "gamma": 90},
        "atoms": [
            {"element": "Si", "position": [0.0, 0.0, 0.0]},
            {"element": "Si", "position": [0.25, 0.25, 0.25]},
        ],
        "num_atoms": 2,
        "source": "Materials Project (mock)",
    },
    {
        "material_id": "mp-30",
        "formula": "Cu",
        "structure_type": "FCC",
        "space_group": "Fm-3m",
        "lattice_parameters": {"a": 3.615, "b": 3.615, "c": 3.615, "alpha": 90, "beta": 90, "gamma": 90},
        "atoms": [
            {"element": "Cu", "position": [0.0, 0.0, 0.0]},
        ],
        "num_atoms": 1,
        "source": "Materials Project (mock)",
    },
    {
        "material_id": "mp-22862",
        "formula": "NaCl",
        "structure_type": "rock salt",
        "space_group": "Fm-3m",
        "lattice_parameters": {"a": 5.640, "b": 5.640, "c": 5.640, "alpha": 90, "beta": 90, "gamma": 90},
        "atoms": [
            {"element": "Na", "position": [0.0, 0.0, 0.0]},
            {"element": "Cl", "position": [0.5, 0.5, 0.5]},
        ],
        "num_atoms": 2,
        "source": "Materials Project (mock)",
    },
    {
        "material_id": "mp-2657",
        "formula": "GaAs",
        "structure_type": "zinc blende",
        "space_group": "F-43m",
        "lattice_parameters": {"a": 5.653, "b": 5.653, "c": 5.653, "alpha": 90, "beta": 90, "gamma": 90},
        "atoms": [
            {"element": "Ga", "position": [0.0, 0.0, 0.0]},
            {"element": "As", "position": [0.25, 0.25, 0.25]},
        ],
        "num_atoms": 2,
        "source": "Materials Project (mock)",
    },
    {
        "material_id": "mp-48",
        "formula": "Al",
        "structure_type": "FCC",
        "space_group": "Fm-3m",
        "lattice_parameters": {"a": 4.049, "b": 4.049, "c": 4.049, "alpha": 90, "beta": 90, "gamma": 90},
        "atoms": [
            {"element": "Al", "position": [0.0, 0.0, 0.0]},
        ],
        "num_atoms": 1,
        "source": "Materials Project (mock)",
    },
]


class MockStructureConnector(BaseStructureConnector):
    """Mock connector returning preset crystal structure data."""

    def search(self, formula: str, **kwargs) -> list:
        """Search structures by chemical formula."""
        formula_upper = formula.strip().upper()
        results = []
        for s in MOCK_STRUCTURES:
            if formula_upper in s["formula"].upper():
                results.append(s)
        return results

    def get_structure(self, material_id: str) -> Optional[dict]:
        """Get structure by material ID."""
        for s in MOCK_STRUCTURES:
            if s["material_id"] == material_id:
                return s
        return None
