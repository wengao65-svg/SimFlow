"""Structure MCP Server.

Provides crystal structure search and management tools.
Supports multiple backends: materials_project, cod.
Falls back to mock connector when credentials are missing.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "runtime"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from connectors.mock import MockStructureConnector
from connectors.materials_project import MaterialsProjectConnector
from connectors.cod import CODConnector
from mcp.shared.transport import dispatch_request, run_server


_CONNECTORS = {
    "mock": MockStructureConnector,
    "materials_project": MaterialsProjectConnector,
    "cod": CODConnector,
}

_mock = MockStructureConnector()


def _get_connector(backend: str = "auto"):
    """Get a connector instance, with auto-detection and fallback."""
    if backend == "auto":
        import os
        if os.environ.get("MP_API_KEY"):
            return MaterialsProjectConnector()
        return CODConnector()
    cls = _CONNECTORS.get(backend)
    if cls is None:
        return None
    try:
        return cls()
    except Exception:
        return _mock


def handle_search(params: dict) -> dict:
    """Search for crystal structures by formula."""
    formula = params.get("formula", "")
    backend = params.get("backend", "auto")
    if not formula:
        return {"status": "error", "message": "formula is required"}

    connector = _get_connector(backend)
    if connector is None:
        return {"status": "error", "message": "Unknown backend: {}".format(backend)}

    results = connector.search(formula)
    return {
        "status": "success",
        "data": {"formula": formula, "results": results, "count": len(results)},
    }


def handle_get(params: dict) -> dict:
    """Get structure data by material ID or COD ID."""
    material_id = params.get("material_id", "")
    backend = params.get("backend", "auto")
    if not material_id:
        return {"status": "error", "message": "material_id is required"}

    connector = _get_connector(backend)
    if connector is None:
        return {"status": "error", "message": "Unknown backend: {}".format(backend)}

    structure = connector.get_structure(material_id)
    if structure is None:
        return {"status": "error", "message": "Material not found: {}".format(material_id), "code": "NOT_FOUND"}
    return {"status": "success", "data": structure}


TOOLS = {
    "search": handle_search,
    "get": handle_get,
}


def handle_request(request: dict) -> dict:
    """Dispatch a request to the appropriate tool handler."""
    return dispatch_request(request, TOOLS)


if __name__ == "__main__":
    run_server(TOOLS)
