"""Official VASP documentation lookup helpers."""

from __future__ import annotations

import re
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from html import unescape
from typing import Any


OFFICIAL_SOURCES = {
    "vasp_wiki": "https://www.vasp.at/wiki/index.php?search={query}",
    "py4vasp": "https://www.vasp.at/py4vasp/latest/search.html?q={query}",
}


def _fetch(url: str, timeout: int = 10) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": "SimFlow VASP lookup"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")


def _compact_html(html: str, limit: int = 800) -> str:
    text = re.sub(r"<script.*?</script>|<style.*?</style>", " ", html, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    text = unescape(re.sub(r"\s+", " ", text)).strip()
    return text[:limit]


def lookup_vasp_docs(query: str, source: str = "auto", fetch: bool = True) -> dict[str, Any]:
    """Lookup official VASP/py4vasp docs and return source-bearing metadata."""
    selected = list(OFFICIAL_SOURCES) if source == "auto" else [source]
    retrieved_at = datetime.now(timezone.utc).isoformat()
    results = []

    for key in selected:
        if key not in OFFICIAL_SOURCES:
            continue
        url = OFFICIAL_SOURCES[key].format(query=urllib.parse.quote_plus(query))
        item = {"source": key, "url": url, "retrieved_at": retrieved_at}
        if fetch:
            try:
                item["summary"] = _compact_html(_fetch(url))
                item["status"] = "success"
            except Exception as exc:
                item["summary"] = "Official lookup failed; verify this topic manually against the linked source."
                item["status"] = "unavailable"
                item["error"] = str(exc)
        else:
            item["summary"] = "Fetch disabled; use this official URL for verification."
            item["status"] = "planned"
        results.append(item)

    return {"query": query, "results": results}


def summarize_troubleshooting(issue: str, context: dict[str, Any] | None = None, fetch: bool = True) -> dict[str, Any]:
    """Generate a conservative troubleshooting summary backed by official links."""
    context = context or {}
    docs = lookup_vasp_docs(issue, source="auto", fetch=fetch)
    return {
        "issue": issue,
        "context": context,
        "summary": (
            "Consult the official VASP Wiki or py4vasp documentation before changing parameters or workflow steps. "
            "SimFlow provides only a source-backed summary and does not infer uncertain VASP version behavior."
        ),
        "sources": docs["results"],
    }
