"""Normalize offline research sources for literature-stage workflows."""

from __future__ import annotations

from pathlib import Path
from typing import Any


SOURCE_TYPES = ("pdf", "bibtex", "doi", "note")
FILE_SOURCE_TYPES = {"pdf", "bibtex"}


def empty_research_source_inputs() -> dict[str, list[Any]]:
    """Return the canonical empty source-input payload."""
    return {
        "pdf": [],
        "bibtex": [],
        "doi": [],
        "note": [],
        "sources": [],
    }


def normalize_research_sources(source_inputs: dict[str, Any] | None, project_root: str | Path = ".") -> dict:
    """Normalize offline research sources into a canonical bundle."""
    counts = {source_type: 0 for source_type in SOURCE_TYPES}
    items: list[dict[str, Any]] = []
    root = Path(project_root).expanduser().resolve()
    payload = empty_research_source_inputs()
    if source_inputs:
        for key, value in source_inputs.items():
            if key in payload and isinstance(value, list):
                payload[key] = value

    def append_item(source_type: str, data: dict[str, Any]) -> None:
        counts[source_type] += 1
        item = {
            "source_id": f"src_{source_type}_{counts[source_type]:03d}",
            "type": source_type,
            **data,
        }
        items.append(item)

    for raw_path in payload["pdf"]:
        path, label = _normalize_local_path(raw_path, root)
        append_item("pdf", {"path": path, "label": label})

    for raw_path in payload["bibtex"]:
        path, label = _normalize_local_path(raw_path, root)
        append_item("bibtex", {"path": path, "label": label})

    for raw_doi in payload["doi"]:
        doi = str(raw_doi).strip()
        if doi:
            append_item("doi", {"doi": doi, "label": doi})

    for raw_note in payload["note"]:
        note = str(raw_note).strip()
        if note:
            append_item("note", {"text": note, "label": f"note-{counts['note'] + 1}"})

    for source in payload["sources"]:
        normalized = _normalize_source_object(source, root)
        append_item(normalized["type"], normalized["data"])

    return {
        "bundle_version": "1.0",
        "counts": counts,
        "total_items": len(items),
        "items": items,
    }


def _normalize_source_object(source: Any, project_root: Path) -> dict[str, Any]:
    if not isinstance(source, dict):
        raise ValueError("Research source objects must be dictionaries")

    source_type = str(source.get("type", "")).strip().lower()
    if source_type not in SOURCE_TYPES:
        raise ValueError(f"Unsupported research source type: {source_type or 'unknown'}")

    if source_type in FILE_SOURCE_TYPES:
        raw_path = source.get("path") or source.get("file") or source.get("value")
        if not raw_path:
            raise ValueError(f"Research source type {source_type} requires a path")
        path, label = _normalize_local_path(raw_path, project_root)
        return {
            "type": source_type,
            "data": {
                "path": path,
                "label": str(source.get("label") or label),
            },
        }

    if source_type == "doi":
        doi = str(source.get("doi") or source.get("id") or source.get("value") or "").strip()
        if not doi:
            raise ValueError("Research source type doi requires a DOI value")
        return {
            "type": source_type,
            "data": {
                "doi": doi,
                "label": str(source.get("label") or doi),
            },
        }

    note = str(source.get("text") or source.get("note") or source.get("value") or "").strip()
    if not note:
        raise ValueError("Research source type note requires note text")
    title = str(source.get("label") or source.get("title") or f"note-{source_type}")
    return {
        "type": source_type,
        "data": {
            "text": note,
            "label": title,
        },
    }


def _normalize_local_path(raw_path: Any, project_root: Path) -> tuple[str, str]:
    candidate = Path(str(raw_path)).expanduser()
    resolved = candidate.resolve() if candidate.is_absolute() else (project_root / candidate).resolve()
    if not resolved.is_file():
        raise FileNotFoundError(f"Research source file not found: {raw_path}")

    try:
        stored_path = resolved.relative_to(project_root).as_posix()
    except ValueError:
        stored_path = resolved.as_posix()
    return stored_path, resolved.name
