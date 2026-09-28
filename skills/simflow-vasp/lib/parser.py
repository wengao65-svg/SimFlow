"""Base parser interface for computational chemistry output files."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional


@dataclass
class ParseResult:
    """Result of parsing a computational chemistry output file."""
    software: str
    job_type: str
    converged: bool
    total_energy: Optional[float] = None
    final_energy: Optional[float] = None
    forces: Optional[list] = None
    stress: Optional[list] = None
    trajectory: Optional[list] = field(default_factory=list)
    kpoints: Optional[dict] = None
    parameters: dict = field(default_factory=dict)
    warnings: list = field(default_factory=list)
    errors: list = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


class BaseParser(ABC):
    """Abstract base class for output file parsers."""

    software: str = "unknown"

    @abstractmethod
    def parse(self, file_path: str) -> ParseResult:
        """Parse an output file and return structured results."""
        ...

    @abstractmethod
    def check_convergence(self, file_path: str) -> dict:
        """Check if the calculation converged."""
        ...

    def _read_file(self, file_path: str) -> str:
        """Read file content."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        return path.read_text(encoding="utf-8", errors="replace")
