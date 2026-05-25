"""SimFlow State MCP Server.

Provides tools for workflow state management.
Tools: read_state, write_state, init_workflow, update_stage,
workflow_status, evidence_graph, handoff_summary
"""

import json
import sys
from pathlib import Path

# Add runtime to path
ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "runtime"))

from tools.read_state import execute as read_state
from tools.write_state import execute as write_state
from tools.init_workflow import execute as init_workflow
from tools.update_stage import execute as update_stage
from tools.workflow_status import execute as workflow_status
from tools.evidence_graph import execute as evidence_graph
from tools.handoff_summary import execute as handoff_summary
from mcp.shared.stdio_server import run_mcp_server

TOOLS = {
    "read_state": read_state,
    "write_state": write_state,
    "init_workflow": init_workflow,
    "update_stage": update_stage,
    "workflow_status": workflow_status,
    "evidence_graph": evidence_graph,
    "handoff_summary": handoff_summary,
}

TOOL_DESCRIPTIONS = {
    "read_state": "Read a SimFlow workflow state file.",
    "write_state": "Write a SimFlow workflow state file.",
    "init_workflow": "Initialize a SimFlow workflow state tree.",
    "update_stage": "Update the current SimFlow stage status.",
    "workflow_status": "Build a read-only SimFlow project status summary.",
    "evidence_graph": "Build a read-only SimFlow artifact evidence graph.",
    "handoff_summary": "Build a compact read-only SimFlow handoff summary.",
}

TOOL_SCHEMAS = {
    "read_state": {
        "type": "object",
        "properties": {
            "project_root": {"type": "string"},
            "file": {"type": "string"},
        },
        "additionalProperties": False,
    },
    "write_state": {
        "type": "object",
        "required": ["project_root", "data"],
        "properties": {
            "project_root": {"type": "string"},
            "file": {"type": "string"},
            "data": {"type": "object"},
        },
        "additionalProperties": False,
    },
    "init_workflow": {
        "type": "object",
        "required": ["project_root", "workflow_type"],
        "properties": {
            "project_root": {"type": "string"},
            "workflow_type": {"type": "string"},
            "entry_point": {"type": "string"},
        },
        "additionalProperties": False,
    },
    "update_stage": {
        "type": "object",
        "required": ["project_root", "stage_name", "status"],
        "properties": {
            "project_root": {"type": "string"},
            "stage_name": {"type": "string"},
            "status": {"type": "string"},
        },
        "additionalProperties": False,
    },
    "workflow_status": {
        "type": "object",
        "required": ["project_root"],
        "properties": {
            "project_root": {"type": "string"},
        },
        "additionalProperties": False,
    },
    "evidence_graph": {
        "type": "object",
        "required": ["project_root"],
        "properties": {
            "project_root": {"type": "string"},
            "stage": {"type": "string"},
            "artifact_id": {"type": "string"},
        },
        "additionalProperties": False,
    },
    "handoff_summary": {
        "type": "object",
        "required": ["project_root"],
        "properties": {
            "project_root": {"type": "string"},
        },
        "additionalProperties": False,
    },
}


def handle_request(request: dict) -> dict:
    """Handle an MCP request."""
    tool = request.get("tool")
    params = request.get("params", {})
    if tool not in TOOLS:
        return {"status": "error", "message": f"Unknown tool: {tool}"}
    try:
        return TOOLS[tool](params)
    except Exception as e:
        return {"status": "error", "message": str(e)}


if __name__ == "__main__":
    run_mcp_server("simflow_state", TOOLS, TOOL_DESCRIPTIONS, TOOL_SCHEMAS)
