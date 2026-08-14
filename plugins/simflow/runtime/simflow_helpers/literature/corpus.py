"""Local PDF and BibTeX corpus intake for corpus-first literature search."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

from .identity import normalize_arxiv_id, normalize_doi, normalize_title


DOI_IN_TEXT_RE = re.compile(r"10\.\d{4,9}/[-._;()/:A-Z0-9]+", re.IGNORECASE)
ARXIV_IN_TEXT_RE = re.compile(
    r"(?:arXiv:\s*)?(\d{4}\.\d{4,5}(?:v\d+)?|[a-z-]+(?:\.[A-Z]{2})?/\d{7}(?:v\d+)?)",
    re.IGNORECASE,
)


def ingest_research_sources(
    research_sources: dict[str, Any] | None,
    *,
    project_root: str | Path,
    extract_pdf_metadata: bool = True,
) -> dict[str, Any]:
    """Read a normalized source bundle into helper-local paper observations."""
    root = Path(project_root).expanduser().resolve()
    records: list[dict[str, Any]] = []
    issues: list[dict[str, Any]] = []
    source_results: list[dict[str, Any]] = []

    for item in (research_sources or {}).get("items", []):
        source_type = item.get("type")
        source_id = item.get("source_id") or "unknown"
        try:
            if source_type == "bibtex":
                path = _resolve_source_path(item.get("path"), root)
                parsed = parse_bibtex(path.read_text(encoding="utf-8"))
                for entry in parsed["entries"]:
                    records.append(_bibtex_record(entry, path, root, source_id))
                for issue in parsed["issues"]:
                    issues.append({"source_id": source_id, "path": _display_path(path, root), **issue})
                source_results.append({
                    "source_id": source_id,
                    "type": source_type,
                    "status": "success" if parsed["entries"] else "empty",
                    "records": len(parsed["entries"]),
                })
            elif source_type == "pdf":
                path = _resolve_source_path(item.get("path"), root)
                record, pdf_issues = inspect_local_pdf(
                    path,
                    project_root=root,
                    extract_metadata=extract_pdf_metadata,
                )
                record["source_id"] = source_id
                records.append(record)
                issues.extend({"source_id": source_id, **issue} for issue in pdf_issues)
                source_results.append({
                    "source_id": source_id,
                    "type": source_type,
                    "status": "success" if record["full_text"]["verified"] else "partial",
                    "records": 1,
                })
            elif source_type == "doi":
                doi = normalize_doi(item.get("doi"))
                if not doi:
                    raise ValueError(f"Invalid DOI: {item.get('doi')}")
                label = str(item.get("label") or "").strip()
                records.append({
                    "source": "local_doi",
                    "source_id": source_id,
                    "source_pointer": doi,
                    "doi": doi,
                    "identifiers": {"doi": doi},
                    "title": label if normalize_doi(label) != doi else "",
                })
                source_results.append({"source_id": source_id, "type": source_type, "status": "success", "records": 1})
            elif source_type == "note":
                source_results.append({"source_id": source_id, "type": source_type, "status": "ignored", "records": 0})
        except Exception as error:
            issues.append({
                "source_id": source_id,
                "code": "corpus_source_error",
                "message": str(error),
            })
            source_results.append({
                "source_id": source_id,
                "type": source_type,
                "status": "error",
                "records": 0,
                "error": str(error),
            })

    return {
        "schema_version": "simflow.literature_corpus.v1",
        "records": records,
        "issues": issues,
        "source_results": source_results,
        "record_count": len(records),
    }


def records_relevant_to_query(records: list[dict[str, Any]], query: str) -> list[dict[str, Any]]:
    """Return corpus records with a lexical match, retaining unidentified PDFs as seeds."""
    query_terms = _query_terms(query)
    if not query_terms:
        return list(records)
    relevant = []
    for record in records:
        searchable = normalize_title(" ".join([
            str(record.get("title") or ""),
            str(record.get("abstract") or ""),
            str(record.get("venue") or record.get("journal") or ""),
            " ".join(record.get("authors") or []),
        ]))
        if not searchable and (record.get("full_text") or record.get("identifiers")):
            relevant.append(record)
            continue
        overlap = sum(1 for term in query_terms if term in searchable)
        if overlap >= max(1, min(2, len(query_terms))):
            relevant.append(record)
    return relevant


def parse_bibtex(text: str) -> dict[str, Any]:
    """Parse common BibTeX entries without adding a mandatory dependency."""
    entries: list[dict[str, Any]] = []
    issues: list[dict[str, Any]] = []
    index = 0
    while True:
        match = re.search(r"@([A-Za-z]+)\s*([({])", text[index:])
        if not match:
            break
        entry_type = match.group(1).lower()
        opener = match.group(2)
        start = index + match.end()
        closer = ")" if opener == "(" else "}"
        end = _matching_delimiter(text, start, opener, closer)
        if end is None:
            issues.append({"code": "bibtex_unterminated_entry", "message": f"Unterminated @{entry_type} entry"})
            break
        body = text[start:end].strip()
        index = end + 1
        if entry_type in {"comment", "preamble", "string"}:
            continue
        try:
            citation_key, fields_text = _split_first_top_level(body, ",")
            fields = _parse_bibtex_fields(fields_text)
            entries.append({
                "entry_type": entry_type,
                "citation_key": citation_key.strip(),
                "fields": fields,
            })
        except ValueError as error:
            issues.append({"code": "bibtex_parse_error", "message": str(error)})
    return {"entries": entries, "issues": issues}


def inspect_local_pdf(
    path: str | Path,
    *,
    project_root: str | Path,
    extract_metadata: bool = True,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Validate a local PDF and extract bibliographic hints without claiming it was read."""
    root = Path(project_root).expanduser().resolve()
    pdf_path = Path(path).expanduser().resolve()
    with pdf_path.open("rb") as handle:
        header_valid = handle.read(5) == b"%PDF-"
    issues: list[dict[str, Any]] = []
    if not header_valid:
        issues.append({
            "code": "invalid_pdf_header",
            "path": _display_path(pdf_path, root),
            "message": "File does not start with the PDF magic bytes",
        })

    title = pdf_path.stem.replace("_", " ").replace("-", " ").strip()
    authors: list[str] = []
    doi = ""
    arxiv_id = ""
    page_count = None
    extraction_backend = ""
    if extract_metadata and header_valid:
        extracted = _extract_pdf_metadata(pdf_path)
        title = extracted.get("title") or title
        authors = extracted.get("authors") or []
        doi = extracted.get("doi") or ""
        arxiv_id = extracted.get("arxiv_id") or ""
        page_count = extracted.get("page_count")
        extraction_backend = extracted.get("backend") or ""
        if extracted.get("error"):
            issues.append({
                "code": "pdf_metadata_extraction_failed",
                "path": _display_path(pdf_path, root),
                "message": extracted["error"],
            })

    identifiers: dict[str, str] = {}
    if doi:
        identifiers["doi"] = doi
    if arxiv_id:
        identifiers["arxiv"] = arxiv_id
    display_path = _display_path(pdf_path, root)
    record = {
        "source": "local_pdf",
        "source_pointer": display_path,
        "path": display_path,
        "title": title,
        "authors": authors,
        "doi": doi,
        "arxiv_id": arxiv_id,
        "identifiers": identifiers,
        "full_text": {
            "path": display_path,
            "source": "local_pdf",
            "access_basis": "user_provided",
            "is_pdf": True,
            "verified": header_valid,
            "sha256": _sha256(pdf_path),
            "size_bytes": pdf_path.stat().st_size,
            "page_count": page_count,
        },
        "metadata_extraction": {
            "attempted": bool(extract_metadata and header_valid),
            "backend": extraction_backend,
            "full_text_inspected": False,
        },
    }
    return record, issues


def _bibtex_record(entry: dict[str, Any], path: Path, root: Path, source_id: str) -> dict[str, Any]:
    fields = entry["fields"]
    doi = normalize_doi(fields.get("doi"))
    arxiv_id = normalize_arxiv_id(fields.get("eprint")) if str(fields.get("archiveprefix") or "").casefold() == "arxiv" else ""
    identifiers: dict[str, str] = {}
    if doi:
        identifiers["doi"] = doi
    if arxiv_id:
        identifiers["arxiv"] = arxiv_id
    authors = [item.strip() for item in re.split(r"\s+and\s+", fields.get("author", ""), flags=re.IGNORECASE) if item.strip()]
    year = None
    try:
        year = int(str(fields.get("year") or "")[:4])
    except ValueError:
        pass
    return {
        "source": "local_bibtex",
        "source_id": source_id,
        "source_pointer": f"{_display_path(path, root)}#{entry['citation_key']}",
        "citation_key": entry["citation_key"],
        "entry_type": entry["entry_type"],
        "title": _clean_bibtex_text(fields.get("title", "")),
        "authors": authors,
        "year": year,
        "venue": _clean_bibtex_text(fields.get("journal") or fields.get("booktitle") or ""),
        "abstract": _clean_bibtex_text(fields.get("abstract", "")),
        "doi": doi,
        "arxiv_id": arxiv_id,
        "identifiers": identifiers,
        "url": fields.get("url", ""),
    }


def _parse_bibtex_fields(text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    index = 0
    while index < len(text):
        while index < len(text) and (text[index].isspace() or text[index] == ","):
            index += 1
        if index >= len(text):
            break
        name_match = re.match(r"([A-Za-z][A-Za-z0-9_-]*)\s*=\s*", text[index:])
        if not name_match:
            raise ValueError(f"Cannot parse BibTeX field near: {text[index:index + 40]!r}")
        name = name_match.group(1).lower()
        index += name_match.end()
        value, index = _read_bibtex_value(text, index)
        fields[name] = value
    return fields


def _read_bibtex_value(text: str, index: int) -> tuple[str, int]:
    while index < len(text) and text[index].isspace():
        index += 1
    if index >= len(text):
        return "", index
    if text[index] == "{":
        end = _matching_delimiter(text, index + 1, "{", "}")
        if end is None:
            raise ValueError("Unterminated braced BibTeX value")
        return text[index + 1:end].strip(), end + 1
    if text[index] == '"':
        end = index + 1
        escaped = False
        while end < len(text):
            char = text[end]
            if char == '"' and not escaped:
                return text[index + 1:end].strip(), end + 1
            escaped = char == "\\" and not escaped
            if char != "\\":
                escaped = False
            end += 1
        raise ValueError("Unterminated quoted BibTeX value")
    end = index
    while end < len(text) and text[end] != ",":
        end += 1
    return text[index:end].strip(), end


def _matching_delimiter(text: str, start: int, opener: str, closer: str) -> int | None:
    depth = 1
    quoted = False
    escaped = False
    for index in range(start, len(text)):
        char = text[index]
        if char == '"' and not escaped:
            quoted = not quoted
        if not quoted:
            if char == opener:
                depth += 1
            elif char == closer:
                depth -= 1
                if depth == 0:
                    return index
        escaped = char == "\\" and not escaped
        if char != "\\":
            escaped = False
    return None


def _split_first_top_level(text: str, separator: str) -> tuple[str, str]:
    depth = 0
    quoted = False
    escaped = False
    for index, char in enumerate(text):
        if char == '"' and not escaped:
            quoted = not quoted
        elif not quoted:
            if char in "{(":
                depth += 1
            elif char in "})":
                depth = max(0, depth - 1)
            elif char == separator and depth == 0:
                return text[:index], text[index + 1:]
        escaped = char == "\\" and not escaped
        if char != "\\":
            escaped = False
    raise ValueError("BibTeX entry is missing a citation-key separator")


def _extract_pdf_metadata(path: Path) -> dict[str, Any]:
    try:
        import fitz
    except ImportError:
        return {"backend": "", "error": "No optional PDF metadata extractor is installed"}
    try:
        with fitz.open(path) as document:
            metadata = document.metadata or {}
            text = "\n".join(document[index].get_text("text") for index in range(min(3, document.page_count)))
            doi_match = DOI_IN_TEXT_RE.search(text)
            arxiv_match = ARXIV_IN_TEXT_RE.search(text)
            authors = [item.strip() for item in re.split(r"\s*(?:;|\band\b)\s*", metadata.get("author") or "", flags=re.IGNORECASE) if item.strip()]
            return {
                "backend": "pymupdf",
                "title": str(metadata.get("title") or "").strip(),
                "authors": authors,
                "doi": normalize_doi(doi_match.group(0)) if doi_match else "",
                "arxiv_id": normalize_arxiv_id(arxiv_match.group(1)) if arxiv_match else "",
                "page_count": document.page_count,
            }
    except Exception as error:
        return {"backend": "pymupdf", "error": str(error)}


def _resolve_source_path(value: Any, root: Path) -> Path:
    path = Path(str(value or "")).expanduser()
    resolved = path.resolve() if path.is_absolute() else (root / path).resolve()
    if not resolved.is_file():
        raise FileNotFoundError(f"Research source file not found: {value}")
    return resolved


def _display_path(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _clean_bibtex_text(value: Any) -> str:
    text = str(value or "").strip()
    text = re.sub(r"[{}]", "", text)
    return " ".join(text.split())


def _query_terms(query: str) -> list[str]:
    stopwords = {"and", "or", "the", "of", "in", "for", "to", "with", "a", "an", "on", "using", "study"}
    return [term for term in normalize_title(query).split() if len(term) >= 3 and term not in stopwords]


__all__ = [
    "ingest_research_sources",
    "inspect_local_pdf",
    "parse_bibtex",
    "records_relevant_to_query",
]
