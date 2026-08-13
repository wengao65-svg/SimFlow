"""Legal full-text candidate collection and bounded PDF download."""

from __future__ import annotations

import urllib.request
from pathlib import Path
from typing import Any, Callable

from .models import FullTextCandidate
from .retry import retry_with_backoff


DISALLOWED_SOURCE_MARKERS = {"sci-hub", "scihub", "libgen", "library genesis"}


def collect_full_text_candidates(
    paper: dict[str, Any],
    *,
    institutional_adapter: Callable[[dict[str, Any]], list[dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    """Collect user-provided and legal OA locations, with an optional host adapter."""
    candidates: list[FullTextCandidate] = []
    issues: list[dict[str, Any]] = []

    for observation in paper.get("observations", []):
        full_text = observation.get("full_text") or {}
        if full_text.get("path") and full_text.get("verified"):
            candidates.append(FullTextCandidate(
                path=full_text["path"],
                source=observation.get("source") or "local_pdf",
                access_basis="user_provided",
                is_pdf=bool(full_text.get("is_pdf", True)),
                verified=bool(full_text.get("verified")),
            ))

    for full_text in paper.get("local_full_text", []):
        if full_text.get("path") and full_text.get("verified"):
            candidates.append(FullTextCandidate(
                path=full_text["path"],
                source=full_text.get("source") or "local_pdf",
                access_basis="user_provided",
                is_pdf=bool(full_text.get("is_pdf", True)),
                verified=True,
            ))

    for location in paper.get("open_access_locations", []):
        if not location.get("is_oa"):
            continue
        url = location.get("pdf_url") or location.get("landing_page_url") or ""
        source = location.get("host_type") or "open_access"
        if not url or _disallowed_source(url) or _disallowed_source(source):
            issues.append({"code": "disallowed_full_text_source", "source": source})
            continue
        candidates.append(FullTextCandidate(
            url=url,
            source=source,
            access_basis="open_access",
            version=location.get("version") or "",
            license=location.get("license") or "",
            is_pdf=bool(location.get("pdf_url")),
            verified=False,
        ))

    if institutional_adapter is not None:
        try:
            adapter_candidates = institutional_adapter(paper) or []
        except Exception as error:
            issues.append({"code": "institutional_adapter_error", "message": str(error)})
            adapter_candidates = []
        for raw in adapter_candidates:
            source = str(raw.get("source") or "institutional_adapter")
            if _disallowed_source(source) or _disallowed_source(raw.get("url")):
                issues.append({"code": "disallowed_full_text_source", "source": source})
                continue
            if raw.get("access_basis") not in {"institutional_entitlement", "publisher_api"}:
                issues.append({"code": "invalid_adapter_access_basis", "source": source})
                continue
            candidates.append(FullTextCandidate(
                url=str(raw.get("url") or ""),
                path=str(raw.get("path") or ""),
                source=source,
                access_basis=raw["access_basis"],
                version=str(raw.get("version") or ""),
                license=str(raw.get("license") or ""),
                is_pdf=bool(raw.get("is_pdf", True)),
                verified=bool(raw.get("verified", False)),
            ))

    deduped = {}
    for candidate in candidates:
        key = (candidate.path, candidate.url, candidate.access_basis)
        deduped[key] = candidate
    ordered = sorted(deduped.values(), key=_candidate_priority)
    return {
        "schema_version": "simflow.full_text_candidates.v1",
        "candidates": [candidate.to_dict() for candidate in ordered],
        "issues": issues,
    }


def download_full_text(candidate: dict[str, Any], output_path: str | Path) -> dict[str, Any]:
    """Download one declared legal PDF candidate and validate its content type."""
    if candidate.get("access_basis") not in {"open_access", "institutional_entitlement", "publisher_api"}:
        raise ValueError("Only OA or explicitly entitled candidates may be downloaded")
    url = str(candidate.get("url") or "")
    if not url or _disallowed_source(url) or _disallowed_source(candidate.get("source")):
        raise ValueError("Missing or disallowed full-text URL")
    destination = Path(output_path).expanduser().resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    success, result = retry_with_backoff(
        lambda: _download_bytes(url),
        max_retries=2,
        base_delay=2.0,
        max_delay=8.0,
    )
    if not success:
        raise result
    data = result
    if not data.startswith(b"%PDF-"):
        raise ValueError("Downloaded content is not a PDF")
    destination.write_bytes(data)
    return {
        "status": "success",
        "path": str(destination),
        "size_bytes": len(data),
        "source": candidate.get("source"),
        "access_basis": candidate.get("access_basis"),
    }


def acquire_full_text(candidate: dict[str, Any], output_path: str | Path) -> dict[str, Any]:
    """Attempt one download without turning acquisition failure into task failure."""
    try:
        result = download_full_text(candidate, output_path)
    except Exception as error:
        return {
            "status": "error",
            "path": str(Path(output_path).expanduser()),
            "source": candidate.get("source"),
            "access_basis": candidate.get("access_basis"),
            "error": str(error),
            "retryable": _retryable(error),
            "metrics": {"attempts": 1, "successes": 0},
        }
    result["metrics"] = {"attempts": 1, "successes": 1}
    return result


def _download_bytes(url: str) -> bytes:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "SimFlow/1.2.0-dev.0 (https://github.com/wengao65-svg/SimFlow)",
            "Accept": "application/pdf",
        },
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()


def _candidate_priority(candidate: FullTextCandidate) -> tuple[int, int]:
    basis_order = {
        "user_provided": 0,
        "open_access": 1,
        "publisher_api": 2,
        "institutional_entitlement": 3,
    }
    return (basis_order.get(candidate.access_basis, 99), 0 if candidate.is_pdf else 1)


def _disallowed_source(value: Any) -> bool:
    text = str(value or "").casefold()
    return any(marker in text for marker in DISALLOWED_SOURCE_MARKERS)


def _retryable(error: Exception) -> bool:
    from .retry import is_retryable

    return is_retryable(error)


__all__ = ["acquire_full_text", "collect_full_text_candidates", "download_full_text"]
