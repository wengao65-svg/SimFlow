"""User-visible file metadata without SimFlow project state or hash chains."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def source_file_record(path: str | Path, *, role: str | None = None) -> dict[str, Any]:
    """Return lightweight metadata for a user-provided source file."""
    candidate = Path(path).expanduser()
    record: dict[str, Any] = {
        "path": str(candidate),
        "present": candidate.exists(),
        "is_file": candidate.is_file(),
        "bytes": candidate.stat().st_size if candidate.is_file() else None,
    }
    if role:
        record["role"] = role
    return record
