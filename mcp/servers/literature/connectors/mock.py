"""Mock literature search connector with preset data."""

from typing import Optional
from .base import BaseLiteratureConnector


MOCK_PAPERS = [
    {
        "doi": "10.1103/PhysRevB.97.165202",
        "title": "First-principles study of silicon crystal structure",
        "authors": ["Zhang, Wei", "Li, Xiaoming"],
        "journal": "Physical Review B",
        "year": 2018,
        "abstract": "We present a comprehensive first-principles study of the electronic and structural properties of silicon using density functional theory.",
        "tags": ["Si", "DFT", "crystal structure"],
    },
    {
        "doi": "10.1021/acs.jpcc.1234567",
        "title": "Ab initio molecular dynamics of liquid water",
        "authors": ["Chen, Yuki", "Wang, Hiroshi"],
        "journal": "Journal of Physical Chemistry C",
        "year": 2021,
        "abstract": "Ab initio molecular dynamics simulations reveal the hydrogen bonding network in liquid water at various temperatures.",
        "tags": ["H2O", "AIMD", "liquid water"],
    },
    {
        "doi": "10.1038/s41467-022-12345-6",
        "title": "Copper nanoparticle melting behavior from MD simulations",
        "authors": ["Kim, Soo-Jin", "Park, Ji-Hoon"],
        "journal": "Nature Communications",
        "year": 2022,
        "abstract": "Molecular dynamics simulations using EAM potentials reveal size-dependent melting behavior in copper nanoparticles.",
        "tags": ["Cu", "MD", "nanoparticle", "melting"],
    },
    {
        "doi": "10.1016/j.actamat.2023.118001",
        "title": "High-throughput DFT screening of alloy surfaces",
        "authors": ["Liu, Fang", "Garcia, Antonio"],
        "journal": "Acta Materialia",
        "year": 2023,
        "abstract": "A high-throughput DFT study of surface energies and catalytic properties of binary alloy surfaces.",
        "tags": ["alloy", "DFT", "surface", "high-throughput"],
    },
    {
        "doi": "10.1103/PhysRevLett.130.016101",
        "title": "Gaussian approximation for electron-phonon coupling",
        "authors": ["Müller, Hans", "Rossi, Maria"],
        "journal": "Physical Review Letters",
        "year": 2023,
        "abstract": "We develop a Gaussian approximation method for computing electron-phonon coupling in semiconductors.",
        "tags": ["electron-phonon", "semiconductor", "Gaussian"],
    },
]


class MockLiteratureConnector(BaseLiteratureConnector):
    """Mock connector returning preset literature data."""

    def search(self, query: str, max_results: int = 20, **kwargs) -> list:
        """Search mock papers by query string."""
        query_lower = query.lower()
        results = []
        for paper in MOCK_PAPERS:
            # Match against title, abstract, and tags
            searchable = (
                paper["title"].lower()
                + " " + paper["abstract"].lower()
                + " " + " ".join(paper["tags"])
            ).lower()
            if query_lower in searchable or any(q in searchable for q in query_lower.split()):
                results.append(paper)
            if len(results) >= max_results:
                break
        return results

    def get_metadata(self, doi: str) -> Optional[dict]:
        """Get metadata for a specific DOI."""
        for paper in MOCK_PAPERS:
            if paper["doi"] == doi:
                return paper
        return None
