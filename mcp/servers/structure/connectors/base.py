"""Base connector for crystal structure search."""

from abc import ABC, abstractmethod
from typing import Optional


class BaseStructureConnector(ABC):
    """Abstract base for structure search connectors."""

    @abstractmethod
    def search(self, formula: str, **kwargs) -> list:
        """Search for crystal structures by formula."""
        ...

    @abstractmethod
    def get_structure(self, material_id: str) -> Optional[dict]:
        """Get structure data by material ID."""
        ...
