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
    tool = request.get("tool")
    params = request.get("params", {})
    if tool not in TOOLS:
        return {"status": "error", "message": f"Unknown tool: {tool}"}
    try:
        return TOOLS[tool](params)
    except Exception as e:
        return {"status": "error", "message": str(e)}


if __name__ == "__main__":
    run_mcp_server("checkpoint_store", TOOLS, TOOL_DESCRIPTIONS, TOOL_SCHEMAS)
