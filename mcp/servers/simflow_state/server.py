"""SimFlow State MCP Server.

Provides tools for workflow state management.
Tools: read_state, write_state, init_workflow, update_stage,
workflow_status, evidence_graph, handoff_summary, stage_readiness,
project_readiness, record_computation_evidence, record_analysis_evidence
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
from tools.stage_readiness import execute as stage_readiness
from tools.project_readiness import execute as project_readiness
from tools.record_computation_evidence import execute as record_computation_evidence
from tools.record_analysis_evidence import execute as record_analysis_evidence
from mcp.shared.stdio_server import run_mcp_server

TOOLS = {
    "read_state": read_state,
    "write_state": write_state,
    "init_workflow": init_workflow,
    "update_stage": update_stage,
    "workflow_status": workflow_status,
    "evidence_graph": evidence_graph,
    "handoff_summary": handoff_summary,
    "stage_readiness": stage_readiness,
    "project_readiness": project_readiness,
    "record_computation_evidence": record_computation_evidence,
    "record_analysis_evidence": record_analysis_evidence,
}

TOOL_DESCRIPTIONS = {
    "read_state": "Read a SimFlow workflow state file.",
    "write_state": "Write a SimFlow workflow state file.",
    "init_workflow": "Initialize a SimFlow workflow state tree.",
    "update_stage": "Update the current SimFlow stage status.",
    "workflow_status": "Build a read-only SimFlow project status summary.",
    "evidence_graph": "Build a read-only SimFlow artifact evidence graph.",
    "handoff_summary": "Build a compact read-only SimFlow handoff summary.",
    "stage_readiness": "Build a read-only readiness diagnostic for one SimFlow stage.",
    "project_readiness": "Build read-only readiness diagnostics for a SimFlow project.",
    "record_computation_evidence": "Record user-provided computation evidence for tracked-only or unknown tools.",
    "record_analysis_evidence": "Record user-provided analysis/visualization evidence for custom or tracked-only workflows.",
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
            "entry_point": {
                "type": "string",
                "enum": [
                    "literature_review",
                    "proposal",
                    "modeling",
                    "computation",
                    "analysis_visualization",
                    "writing",
                ],
            },
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
            "evidence_role": {"type": "string"},
            "tool": {"type": "string"},
            "status": {"type": "string"},
            "schema_version": {"type": "string"},
            "recipe": {"type": "string"},
            "claim_id": {"type": "string"},
            "direction": {"type": "string", "enum": ["upstream", "downstream", "both"]},
            "depth": {"type": "integer", "minimum": 0, "maximum": 5},
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
    "stage_readiness": {
        "type": "object",
        "required": ["project_root"],
        "properties": {
            "project_root": {"type": "string"},
            "stage": {"type": "string"},
        },
        "additionalProperties": False,
    },
    "project_readiness": {
        "type": "object",
        "required": ["project_root"],
        "properties": {
            "project_root": {"type": "string"},
        },
        "additionalProperties": False,
    },
    "record_computation_evidence": {
        "type": "object",
        "required": ["project_root", "evidence_params"],
        "properties": {
            "project_root": {"type": "string"},
            "evidence_params": {
                "type": "object",
                "properties": {
                    "software": {"type": "string"},
                    "task": {"type": "string"},
                    "command": {"type": "string"},
                    "version": {"type": "string"},
                    "environment": {"type": "object"},
                    "complete_stage": {"type": "boolean"},
                    "parent_artifacts": {"type": "array", "items": {"type": "string"}},
                    "evidence": {"type": "object"},
                },
                "required": ["evidence"],
                "additionalProperties": True,
            },
            "dry_run": {"type": "boolean"},
        },
        "additionalProperties": False,
    },
    "record_analysis_evidence": {
        "type": "object",
        "required": ["project_root", "evidence_params"],
        "properties": {
            "project_root": {"type": "string"},
            "evidence_params": {
                "type": "object",
                "properties": {
                    "software": {"type": "string"},
                    "task": {"type": "string"},
                    "command": {"type": "string"},
                    "version": {"type": "string"},
                    "environment": {"type": "object"},
                    "complete_stage": {"type": "boolean"},
                    "parent_artifacts": {"type": "array", "items": {"type": "string"}},
                    "evidence": {"type": "object"},
                },
                "required": ["evidence"],
                "additionalProperties": True,
            },
            "dry_run": {"type": "boolean"},
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
