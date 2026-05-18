"""Artifact Store MCP Server.

Tools: register, list, get
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "runtime"))

from tools.register import execute as register
from tools.list import execute as list_artifacts
from tools.get import execute as get_artifact
from mcp.shared.stdio_server import run_mcp_server

TOOLS = {
    "register": register,
    "list": list_artifacts,
    "get": get_artifact,
}

TOOL_DESCRIPTIONS = {
    "register": "Register a SimFlow artifact with metadata and lineage.",
    "list": "List registered SimFlow artifacts.",
    "get": "Fetch one registered SimFlow artifact by identifier.",
}

TOOL_SCHEMAS = {
    "register": {
        "type": "object",
        "required": ["project_root", "name", "type", "stage"],
        "properties": {
            "project_root": {"type": "string"},
            "name": {"type": "string"},
            "type": {"type": "string"},
            "stage": {"type": "string"},
            "path": {"type": "string"},
            "parent_artifacts": {"type": "array", "items": {"type": "string"}},
            "parameters": {"type": "object"},
            "software": {"type": "string"},
            "metadata": {"type": "object"},
        },
        "additionalProperties": False,
    },
    "list": {
        "type": "object",
        "properties": {
            "project_root": {"type": "string"},
            "stage": {"type": "string"},
        },
        "additionalProperties": False,
    },
    "get": {
        "type": "object",
        "required": ["artifact_id"],
        "properties": {
            "project_root": {"type": "string"},
            "artifact_id": {"type": "string"},
        },
        "additionalProperties": False,
    },
}


def handle_request(request: dict) -> dict:
    tool = request.get("tool")
    params = request.get("params", {})
    if tool not in TOOLS:
        return {"status": "error", "message": f"Unknown tool: {tool}"}
    try:
        return TOOLS[tool](params)
    except Exception as e:
        return {"status": "error", "message": str(e)}


if __name__ == "__main__":
    run_mcp_server("artifact_store", TOOLS, TOOL_DESCRIPTIONS, TOOL_SCHEMAS)
