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
        "required": ["project_root"],
        "properties": {
            "project_root": {"type": "string"},
            "stage": {"type": "string"},
        },
        "additionalProperties": False,
    },
    "get": {
        "type": "object",
        "required": ["project_root", "artifact_id"],
        "properties": {
            "project_root": {"type": "string"},
            "artifact_id": {"type": "string"},
        },
        "additionalProperties": False,
    },
}


def handle_request(request: dict) -> dict:
    """Handle an MCP request with skill-engagement contract enforcement."""
    tool = request.get("tool")
    params = request.get("params", {})
    if tool not in TOOLS:
        return {"status": "error", "message": f"Unknown tool: {tool}"}

    # Skill-engagement contract: register requires read_state first
    project_root = params.get("project_root")
    if project_root:
        from runtime.simflow_core.engagement import (
            check_prerequisites,
            record_tool_call,
            EngagementViolation,
        )
        full_tool_name = f"artifact_store/{tool}"
        try:
            check_prerequisites(full_tool_name, project_root)
        except EngagementViolation as violation:
            return {
                "status": "error",
                "code": "skill_engagement_contract_violation",
                "message": (
                    f"Before calling {tool}, you must call simflow_state/read_state "
                    f"first in this session. Missing: {violation.missing}"
                ),
                "required_prerequisites": violation.missing,
                "session_start": violation.session_start,
            }
        record_tool_call(full_tool_name, project_root)

    try:
        return TOOLS[tool](params)
    except Exception as e:
        return {"status": "error", "message": str(e)}


if __name__ == "__main__":
    run_mcp_server("artifact_store", TOOLS, TOOL_DESCRIPTIONS, TOOL_SCHEMAS, request_handler=handle_request)
