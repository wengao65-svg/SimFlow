"""Checkpoint Store MCP Server.

Tools: create, list, restore
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "runtime"))

from tools.create import execute as create
from tools.list import execute as list_checkpoints
from tools.restore import execute as restore
from mcp.shared.stdio_server import run_mcp_server

TOOLS = {
    "create": create,
    "list": list_checkpoints,
    "restore": restore,
}

TOOL_DESCRIPTIONS = {
    "create": "Create a SimFlow checkpoint for a workflow stage.",
    "list": "List SimFlow checkpoints.",
    "restore": "Restore workflow state from a SimFlow checkpoint.",
}

TOOL_SCHEMAS = {
    "create": {
        "type": "object",
        "required": ["project_root", "workflow_id", "stage_id"],
        "properties": {
            "project_root": {"type": "string"},
            "workflow_id": {"type": "string"},
            "stage_id": {"type": "string"},
            "description": {"type": "string"},
            "status": {"type": "string"},
            "job_id": {"type": "string"},
        },
        "additionalProperties": False,
    },
    "list": {
        "type": "object",
        "properties": {
            "project_root": {"type": "string"},
        },
        "additionalProperties": False,
    },
    "restore": {
        "type": "object",
        "required": ["project_root", "checkpoint_id"],
        "properties": {
            "project_root": {"type": "string"},
            "checkpoint_id": {"type": "string"},
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

    # Skill-engagement contract: create requires read_state first
    project_root = params.get("project_root")
    if project_root:
        from runtime.simflow_core.engagement import (
            check_prerequisites,
            record_tool_call,
            EngagementViolation,
        )
        full_tool_name = f"checkpoint_store/{tool}"
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
    run_mcp_server("checkpoint_store", TOOLS, TOOL_DESCRIPTIONS, TOOL_SCHEMAS)
