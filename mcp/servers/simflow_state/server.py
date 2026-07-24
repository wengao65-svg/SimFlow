"""SimFlow State MCP Server.

Provides tools for workflow state management.
Tools: read_state, write_state, init_workflow, update_stage,
workflow_status, evidence_graph, handoff_summary, stage_readiness,
project_readiness, record_computation_evidence, record_analysis_evidence,
orphan_compute_scanner
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
from tools.orphan_compute_scanner import execute as orphan_compute_scanner
from tools.record_user_override import execute as record_user_override
from tools.session_handoff import execute as session_handoff
from tools.record_stage_failure import execute as record_stage_failure
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
    "orphan_compute_scanner": orphan_compute_scanner,
    "record_user_override": record_user_override,
    "session_handoff": session_handoff,
    "record_stage_failure": record_stage_failure,
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
    "orphan_compute_scanner": "Scan project root for compute directories not registered in SimFlow state.",
    "record_user_override": "Record a user-approved gate bypass/override decision in gates.json.",
    "session_handoff": "Generate a session-level handoff report with state, warnings, and next steps.",
    "record_stage_failure": "Record an error report, failure artifacts, failed state, and failure checkpoint.",
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
            "force": {
                "type": "boolean",
                "default": False,
                "description": "Back up existing .simflow tree to .simflow/backups/<timestamp>/ and recreate canonical state files. Default false (idempotent).",
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
    "orphan_compute_scanner": {
        "type": "object",
        "required": ["project_root"],
        "properties": {
            "project_root": {"type": "string"},
            "max_depth": {"type": "integer", "default": 3},
        },
        "additionalProperties": False,
    },
    "record_user_override": {
        "type": "object",
        "required": ["project_root", "gate_id", "approver_context", "risk_note"],
        "properties": {
            "project_root": {"type": "string"},
            "gate_id": {"type": "string"},
            "approver_context": {"type": "string"},
            "risk_note": {"type": "string"},
            "requested_action": {"type": "string"},
            "directory_path": {"type": "string"},
            "original_gate_failure_ref": {"type": "string"},
            "stage": {"type": "string"},
        },
        "additionalProperties": False,
    },
    "session_handoff": {
        "type": "object",
        "required": ["project_root"],
        "properties": {
            "project_root": {"type": "string"},
        },
        "additionalProperties": False,
    },
    "record_stage_failure": {
        "type": "object",
        "required": ["project_root", "stage_name", "message"],
        "properties": {
            "project_root": {"type": "string"},
            "stage_name": {"type": "string"},
            "message": {"type": "string"},
            "activity": {"type": "string"},
            "reason_code": {"type": "string"},
            "exception_type": {"type": "string"},
            "traceback": {"type": "string"},
            "job_id": {"type": "string"},
            "partial_artifact_ids": {"type": "array", "items": {"type": "string"}},
            "failure_id": {"type": "string"},
        },
        "additionalProperties": False,
    },
}


def handle_request(request: dict) -> dict:
    """Handle an MCP request with skill-engagement contract enforcement.

    P0.7: State-write tools are blocked unless read_state was called.
    P3.1: When a read-only tool is called and no prior engagement exists,
    auto-record a read_state call so prerequisites are satisfied for
    subsequent state-write tools. This reduces friction: agents that call
    workflow_status or stage_readiness automatically get their read_state
    prerequisite met.
    """
    tool = request.get("tool")
    params = request.get("params", {})
    if tool not in TOOLS:
        return {"status": "error", "message": f"Unknown tool: {tool}"}

    # Skill-engagement contract: check prerequisites for protected tools
    project_root = params.get("project_root")
    if project_root:
        from runtime.simflow_core.engagement import (
            check_prerequisites,
            record_tool_call,
            get_engagement_status,
            EngagementViolation,
            EXEMPT_TOOLS,
        )
        full_tool_name = f"simflow_state/{tool}"

        # P3.1: Auto-read_state for first-call to read-only tools
        # If no prior session exists and this is a read-only tool (not read_state
        # itself, not a state-write tool), auto-record read_state to bootstrap
        # the session. This satisfies the prerequisite for future state-write calls.
        if full_tool_name in EXEMPT_TOOLS and tool not in ("read_state", "init_workflow"):
            status = get_engagement_status(project_root)
            if not status.get("has_session"):
                # No prior engagement — auto-record read_state
                record_tool_call("simflow_state/read_state", project_root)

        try:
            check_prerequisites(full_tool_name, project_root)
        except EngagementViolation as violation:
            return {
                "status": "error",
                "code": "skill_engagement_contract_violation",
                "message": (
                    f"Before calling {tool}, you must call read_state first in "
                    f"this session. Load the relevant SimFlow skill and engage "
                    f"the workflow layer via MCP tools. Missing: {violation.missing}"
                ),
                "required_prerequisites": violation.missing,
                "session_start": violation.session_start,
            }
        # Record the tool call after prerequisite check passes
        record_tool_call(full_tool_name, project_root)

    try:
        return TOOLS[tool](params)
    except Exception as e:
        return {"status": "error", "message": str(e)}


if __name__ == "__main__":
    run_mcp_server("simflow_state", TOOLS, TOOL_DESCRIPTIONS, TOOL_SCHEMAS)
