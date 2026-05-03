"""arXiv literature connector."""

import re
import urllib.parse
import urllib.request
from typing import Optional
from xml.etree import ElementTree

from .base import BaseLiteratureConnector


ARXIV_API = "http://export.arxiv.org/api/query"


class ArxivConnector(BaseLiteratureConnector):
    """Connector for arXiv paper search."""

    def search(self, query: str, max_results: int = 20, **kwargs) -> list:
        """Search arXiv for papers."""
        params = urllib.parse.urlencode({
            "search_query": "all:{}".format(query),
            "start": 0,
            "max_results": max_results,
            "sortBy": "relevance",
            "sortOrder": "descending",
        })
        url = "{}?{}".format(ARXIV_API, params)

        try:
            with urllib.request.urlopen(url, timeout=30) as response:
                xml_data = response.read().decode("utf-8")
        except Exception as e:
            return []

        return self._parse_results(xml_data)

    def get_metadata(self, arxiv_id: str) -> Optional[dict]:
        """Get metadata for a specific arXiv paper."""
        # Clean arxiv ID
        arxiv_id = arxiv_id.replace("arXiv:", "").strip()
        params = urllib.parse.urlencode({
            "id_list": arxiv_id,
            "max_results": 1,
        })
        url = "{}?{}".format(ARXIV_API, params)

        try:
            with urllib.request.urlopen(url, timeout=30) as response:
                xml_data = response.read().decode("utf-8")
        except Exception:
            return None

        results = self._parse_results(xml_data)
        return results[0] if results else None

    def _parse_results(self, xml_data: str) -> list:
        """Parse arXiv Atom XML response."""
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        try:
            root = ElementTree.fromstring(xml_data)
        except ElementTree.ParseError:
            return []

        papers = []
        for entry in root.findall("atom:entry", ns):
            title = entry.find("atom:title", ns)
            summary = entry.find("atom:summary", ns)
            published = entry.find("atom:published", ns)
            authors = entry.findall("atom:author/atom:name", ns)

            # Extract arXiv ID from id URL
            id_elem = entry.find("atom:id", ns)
            arxiv_id = ""
            if id_elem is not None and id_elem.text:
                match = re.search(r"(\d+\.\d+)", id_elem.text)
                if match:
                    arxiv_id = match.group(1)

            papers.append({
                "id": arxiv_id,
                "title": title.text.strip().replace("\n", " ") if title is not None else "",
                "authors": [a.text for a in authors if a.text],
                "abstract": summary.text.strip() if summary is not None else "",
                "published": published.text if published is not None else "",
                "source": "arXiv",
                "url": "https://arxiv.org/abs/{}".format(arxiv_id) if arxiv_id else "",
            })

        return papers
