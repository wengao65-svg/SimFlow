"""Compact SimFlow state MCP server.

The public surface deliberately contains four composite tools. Legacy state,
artifact, and checkpoint readers remain internal compatibility APIs and are
not advertised through MCP.
"""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "runtime"))

from mcp.shared.stdio_server import run_mcp_server
from tools.checkpoint import execute as checkpoint
from tools.inspect import execute as inspect
from tools.record import execute as record
from tools.recover import execute as recover


TOOLS = {
    "inspect": inspect,
    "record": record,
    "checkpoint": checkpoint,
    "recover": recover,
}

TOOL_DESCRIPTIONS = {
    "inspect": "Read compact project status, recent records, recovery points, and a read-only legacy migration audit.",
    "record": "Append one logical project record or explicitly confirm a migration audit by hash.",
    "checkpoint": "Create a compact recovery reference containing hashes, restart paths, and restart instructions.",
    "recover": "Validate a compact checkpoint and return recovery readiness without executing compute.",
}

_PATH_REF_SCHEMA = {
    "oneOf": [
        {"type": "string"},
        {
            "type": "object",
            "required": ["path"],
            "properties": {
                "path": {"type": "string"},
                "name": {"type": "string"},
                "role": {"type": "string"},
                "sha256": {"type": "string"},
                "size_bytes": {"type": "integer", "minimum": 0},
                "restricted": {"type": "boolean", "default": False},
                "metadata": {"type": "object"},
            },
            "additionalProperties": True,
        },
    ]
}

TOOL_SCHEMAS = {
    "inspect": {
        "type": "object",
        "required": ["project_root"],
        "properties": {
            "project_root": {"type": "string"},
            "kind": {
                "type": "string",
                "enum": [
                    "milestone", "run", "artifact", "analysis", "approval",
                    "failure", "note", "checkpoint", "recovery", "migration",
                ],
            },
            "status": {"type": "string"},
            "record_id": {"type": "string"},
            "run_id": {"type": "string"},
            "limit": {"type": "integer", "minimum": 1, "maximum": 200, "default": 20},
            "include_legacy": {"type": "boolean", "default": True},
        },
        "additionalProperties": False,
    },
    "record": {
        "type": "object",
        "required": ["project_root", "kind", "summary"],
        "properties": {
            "project_root": {"type": "string"},
            "kind": {
                "type": "string",
                "enum": ["milestone", "run", "artifact", "analysis", "approval", "failure", "note", "migration"],
            },
            "summary": {"type": "string", "minLength": 1},
            "status": {"type": "string"},
            "stage": {"type": "string"},
            "run_id": {"type": "string"},
            "goal": {"type": "string"},
            "next_action": {"type": ["string", "object", "array"]},
            "artifacts": {"type": "array", "items": _PATH_REF_SCHEMA},
            "parent_ids": {"type": "array", "items": {"type": "string"}},
            "details": {"type": "object"},
            "migration_report_hash": {"type": "string"},
            "confirm_migration": {"type": "boolean", "default": False},
        },
        "additionalProperties": False,
    },
    "checkpoint": {
        "type": "object",
        "required": ["project_root", "summary"],
        "properties": {
            "project_root": {"type": "string"},
            "summary": {"type": "string", "minLength": 1},
            "status": {"type": "string", "enum": ["ready", "partial", "diagnostic"], "default": "ready"},
            "record_id": {"type": "string"},
            "run_id": {"type": "string"},
            "milestone_id": {"type": "string"},
            "input_refs": {"type": "array", "items": _PATH_REF_SCHEMA},
            "restart_refs": {"type": "array", "items": _PATH_REF_SCHEMA},
            "resume_command": {"type": "string"},
            "risk_notes": {"type": "array", "items": {"type": "string"}},
        },
        "additionalProperties": False,
    },
    "recover": {
        "type": "object",
        "required": ["project_root"],
        "properties": {
            "project_root": {"type": "string"},
            "checkpoint_id": {"type": "string"},
        },
        "additionalProperties": False,
    },
}


def handle_request(request: dict) -> dict:
    tool = request.get("tool")
    if tool not in TOOLS:
        return {"status": "error", "message": f"Unknown tool: {tool}"}
    try:
        return TOOLS[tool](request.get("params", {}))
    except Exception as error:
        return {"status": "error", "message": str(error)}


if __name__ == "__main__":
    run_mcp_server("simflow_state", TOOLS, TOOL_DESCRIPTIONS, TOOL_SCHEMAS, request_handler=handle_request)
