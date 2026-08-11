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
    "inspect": "Read project status, relevant Experiment memory, operational records, recovery points, and a read-only legacy audit.",
    "record": "Append one operational record or one schema-discriminated Experiment notebook entry.",
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

_EXPERIMENT_PAYLOAD_SCHEMAS = {
    "experiment": {
        "type": "object",
        "properties": {
            "title": {"type": "string", "minLength": 1},
            "research_question": {"type": "string", "minLength": 1},
            "scope_paths": {"type": "array", "items": {"type": "string"}, "minItems": 1},
            "tags": {"type": "array", "items": {"type": "string"}},
            "status": {"type": "string", "enum": ["active", "paused", "completed", "abandoned", "superseded"]},
            "next_action": {"type": ["string", "object", "array"]},
        },
        "additionalProperties": False,
    },
    "attempt": {
        "type": "object",
        "properties": {
            "attempt_id": {"type": "string"}, "method": {"type": "string"},
            "parameters": {"type": "object"}, "acceptance_criteria": {"type": ["array", "object", "string"]},
            "software": {"type": ["string", "object"]}, "status": {"type": "string"},
            "evidence": {"type": "array", "items": _PATH_REF_SCHEMA},
            "next_action": {"type": ["string", "object", "array"]}, "details": {"type": "object"},
        },
        "additionalProperties": False,
    },
    "observation": {
        "type": "object",
        "properties": {
            "attempt_id": {"type": "string"}, "status": {"type": "string"},
            "evidence": {"type": "array", "items": _PATH_REF_SCHEMA},
            "next_action": {"type": ["string", "object", "array"]}, "details": {"type": "object"},
            "uncertainty": {"type": ["string", "object", "array"]},
        },
        "additionalProperties": False,
    },
    "decision": {
        "type": "object",
        "properties": {
            "attempt_id": {"type": "string"}, "status": {"type": "string"},
            "outcome": {"type": ["string", "object"]}, "rationale": {"type": "string"},
            "alternatives": {"type": "array"}, "evidence": {"type": "array", "items": _PATH_REF_SCHEMA},
            "next_action": {"type": ["string", "object", "array"]}, "details": {"type": "object"},
        },
        "additionalProperties": False,
    },
    "material_action": {
        "type": "object",
        "required": ["status", "operation"],
        "properties": {
            "attempt_id": {"type": "string"},
            "status": {"type": "string", "enum": ["planned", "completed", "partial", "failed", "reverted"]},
            "operation": {"type": "string", "enum": ["delete", "filter", "deduplicate", "overwrite", "truncate", "move", "replace_dataset", "clean_trajectory", "other_evidence_change"]},
            "material_action_id": {"type": "string"}, "targets": {"type": "array", "items": {"type": "string"}},
            "reason": {"type": "string"}, "selection_criteria": {"type": ["string", "object", "array"]},
            "recoverability": {"type": "string", "enum": ["reversible", "partially_reversible", "irreversible"]},
            "outcome": {"type": ["string", "object", "array"]}, "actual_scope": {"type": ["string", "object", "array"]},
            "evidence": {"type": "array", "items": _PATH_REF_SCHEMA},
            "next_action": {"type": ["string", "object", "array"]}, "details": {"type": "object"},
        },
        "additionalProperties": False,
    },
    "recovery": {
        "type": "object",
        "properties": {
            "attempt_id": {"type": "string"}, "status": {"type": "string"},
            "checkpoint_id": {"type": "string"}, "decision": {"type": ["string", "object"]},
            "evidence": {"type": "array", "items": _PATH_REF_SCHEMA},
            "next_action": {"type": ["string", "object", "array"]}, "details": {"type": "object"},
        },
        "additionalProperties": False,
    },
}

_OPERATIONAL_RECORD_PROPERTIES = {
    "project_root": {"type": "string"}, "channel": {"type": "string", "const": "operational"},
    "kind": {"type": "string", "enum": ["milestone", "run", "artifact", "analysis", "approval", "failure", "note", "migration"]},
    "summary": {"type": "string", "minLength": 1}, "status": {"type": "string"},
    "stage": {"type": "string"}, "run_id": {"type": "string"}, "goal": {"type": "string"},
    "next_action": {"type": ["string", "object", "array"]}, "artifacts": {"type": "array", "items": _PATH_REF_SCHEMA},
    "parent_ids": {"type": "array", "items": {"type": "string"}}, "details": {"type": "object"},
    "migration_report_hash": {"type": "string"}, "confirm_migration": {"type": "boolean", "default": False},
    "experiment_id": {"type": "string"}, "attempt_id": {"type": "string"}, "idempotency_key": {"type": "string"},
}

_EXPERIMENT_RECORD_PROPERTIES = {
    "project_root": {"type": "string"}, "channel": {"type": "string", "const": "experiment"},
    "entry_type": {"type": "string", "enum": list(_EXPERIMENT_PAYLOAD_SCHEMAS)},
    "action": {"type": "string", "minLength": 1}, "summary": {"type": "string", "minLength": 1},
    "experiment_id": {"type": "string", "pattern": "^exp_[0-9a-f]{12}$"},
    "parent_entry_ids": {"type": "array", "items": {"type": "string"}},
    "runtime_record_ids": {"type": "array", "items": {"type": "string"}},
    "idempotency_key": {"type": "string"},
    "payload": {"type": "object"},
}

_EXPERIMENT_RECORD_VARIANTS = [
    {
        "required": ["project_root", "channel", "entry_type", "action", "summary", "payload"],
        "properties": {
            "channel": {"const": "experiment"},
            "entry_type": {"const": entry_type},
            "payload": payload_schema,
        },
    }
    for entry_type, payload_schema in _EXPERIMENT_PAYLOAD_SCHEMAS.items()
]

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
            "working_directory": {"type": "string"},
            "query": {"type": "string"},
            "experiment_id": {"type": "string"},
            "attempt_id": {"type": "string"},
            "entry_type": {"type": "string", "enum": list(_EXPERIMENT_PAYLOAD_SCHEMAS)},
        },
        "additionalProperties": False,
    },
    "record": {
        "type": "object",
        "properties": {**_OPERATIONAL_RECORD_PROPERTIES, **_EXPERIMENT_RECORD_PROPERTIES},
        "oneOf": [
            {"required": ["project_root", "kind", "summary"], "properties": {"channel": {"enum": ["operational"]}}},
            *_EXPERIMENT_RECORD_VARIANTS,
        ],
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
            "experiment_id": {"type": "string"},
            "attempt_id": {"type": "string"},
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
