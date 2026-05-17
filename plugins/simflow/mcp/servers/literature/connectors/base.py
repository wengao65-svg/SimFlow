"""Base connector for literature search."""

from abc import ABC, abstractmethod
from typing import Optional


class BaseLiteratureConnector(ABC):
    """Abstract base for literature search connectors."""

    @abstractmethod
    def search(self, query: str, max_results: int = 20, **kwargs) -> list:
        """Search for literature."""
        ...

    @abstractmethod
    def get_metadata(self, doi: str) -> Optional[dict]:
        """Get metadata for a specific DOI."""
        ...
