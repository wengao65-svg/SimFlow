"""Base connector for literature search."""

from abc import ABC, abstractmethod
from typing import Any, Optional

from ..models import ProviderResult
from ..retry import is_retryable


class BaseLiteratureConnector(ABC):
    """Abstract base for literature search connectors."""

    provider_name = "unknown"

    @property
    def last_error(self) -> Exception | None:
        return getattr(self, "_last_error", None)

    @property
    def last_query_count(self) -> int:
        return int(getattr(self, "_last_query_count", 1))

    def _set_error(self, error: Exception | None) -> None:
        self._last_error = error

    def _set_query_count(self, count: int) -> None:
        self._last_query_count = max(0, int(count))

    @abstractmethod
    def search(self, query: str, max_results: int = 20, **kwargs) -> list:
        """Search for literature."""
        ...

    @abstractmethod
    def get_metadata(self, doi: str) -> Optional[dict]:
        """Get metadata for a specific DOI."""
        ...

    def search_result(self, query: str, max_results: int = 20, **kwargs: Any) -> ProviderResult:
        """Search with explicit empty/error distinction."""
        try:
            records = self.search(query, max_results=max_results, **kwargs)
        except Exception as error:
            return ProviderResult(
                provider=self.provider_name,
                operation="search",
                status="error",
                error=str(error),
                retryable=is_retryable(error),
                query_count=self.last_query_count,
            )
        error = self.last_error
        if error is not None:
            return ProviderResult(
                provider=self.provider_name,
                operation="search",
                status="error",
                error=str(error),
                retryable=is_retryable(error),
                query_count=self.last_query_count,
            )
        return ProviderResult(
            provider=self.provider_name,
            operation="search",
            status="success" if records else "empty",
            records=records,
            query_count=self.last_query_count,
        )

    def metadata_result(self, identifier: str) -> ProviderResult:
        """Fetch metadata with explicit empty/error distinction."""
        try:
            record = self.get_metadata(identifier)
        except Exception as error:
            return ProviderResult(
                provider=self.provider_name,
                operation="metadata",
                status="error",
                error=str(error),
                retryable=is_retryable(error),
                query_count=self.last_query_count,
            )
        error = self.last_error
        if error is not None:
            return ProviderResult(
                provider=self.provider_name,
                operation="metadata",
                status="error",
                error=str(error),
                retryable=is_retryable(error),
                query_count=self.last_query_count,
            )
        return ProviderResult(
            provider=self.provider_name,
            operation="metadata",
            status="success" if record else "empty",
            records=[record] if record else [],
            query_count=self.last_query_count,
        )

    def references_result(self, identifier: str, max_results: int = 20) -> ProviderResult:
        """Return papers referenced by the seed when supported."""
        return ProviderResult(
            provider=self.provider_name,
            operation="references",
            status="unsupported",
            query_count=0,
        )

    def citations_result(self, identifier: str, max_results: int = 20) -> ProviderResult:
        """Return papers citing the seed when supported."""
        return ProviderResult(
            provider=self.provider_name,
            operation="citations",
            status="unsupported",
            query_count=0,
        )
