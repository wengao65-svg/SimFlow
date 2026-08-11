"""SimFlow State MCP Server.

Provides tools for workflow state management.
Tools: read_state, write_state, init_workflow, update_stage,
workflow_status, evidence_graph, handoff_summary, stage_readiness,
project_readiness, record_computation_evidence, record_analysis_evidence,
orphan_compute_scanner
and consolidated artifact/checkpoint storage tools
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
from tools.repair_state import execute as repair_state
from tools.register_artifact import execute as register_artifact
from tools.list_artifacts import execute as list_artifacts
from tools.get_artifact import execute as get_artifact
from tools.create_checkpoint import execute as create_checkpoint
from tools.list_checkpoints import execute as list_checkpoints
from tools.restore_checkpoint import execute as restore_checkpoint
from tools.project_reentry import execute as project_reentry
from tools.begin_experiment import execute as begin_experiment
from tools.finish_experiment import execute as finish_experiment
from tools.begin_iteration import execute as begin_iteration
from tools.evaluate_iteration import execute as evaluate_iteration
from tools.start_activity import execute as start_activity
from tools.finish_activity import execute as finish_activity
from tools.experiment_timeline import execute as experiment_timeline
from tools.fork_experiment import execute as fork_experiment
from tools.resume_experiment import execute as resume_experiment
from tools.compare_experiments import execute as compare_experiments
from tools.verify_experiment_ledger import execute as verify_experiment_ledger
from tools.rebuild_experiment_exports import execute as rebuild_experiment_exports
from tools.migrate_experiment_ledger import execute as migrate_experiment_ledger
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
    "repair_state": repair_state,
    "register_artifact": register_artifact,
    "list_artifacts": list_artifacts,
    "get_artifact": get_artifact,
    "create_checkpoint": create_checkpoint,
    "list_checkpoints": list_checkpoints,
    "restore_checkpoint": restore_checkpoint,
    "project_reentry": project_reentry,
    "begin_experiment": begin_experiment,
    "finish_experiment": finish_experiment,
    "begin_iteration": begin_iteration,
    "evaluate_iteration": evaluate_iteration,
    "start_activity": start_activity,
    "finish_activity": finish_activity,
    "experiment_timeline": experiment_timeline,
    "fork_experiment": fork_experiment,
    "resume_experiment": resume_experiment,
    "compare_experiments": compare_experiments,
    "verify_experiment_ledger": verify_experiment_ledger,
    "rebuild_experiment_exports": rebuild_experiment_exports,
    "migrate_experiment_ledger": migrate_experiment_ledger,
}

TOOL_DESCRIPTIONS = {
    "read_state": "Start here for an existing project: read a SimFlow workflow state file.",
    "write_state": "Write a SimFlow workflow state file.",
    "init_workflow": "Initialize a SimFlow workflow state tree.",
    "update_stage": "Update the current SimFlow stage status.",
    "workflow_status": "Start here for an existing project: build a read-only status summary and bootstrap engagement.",
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
    "repair_state": "Audit state inconsistencies or apply backed-up repairs above a confidence threshold.",
    "register_artifact": "Register a SimFlow artifact with metadata and lineage.",
    "list_artifacts": "List registered SimFlow artifacts.",
    "get_artifact": "Fetch one registered SimFlow artifact by identifier.",
    "create_checkpoint": "Create a SimFlow checkpoint for a workflow stage.",
    "list_checkpoints": "List SimFlow checkpoints.",
    "restore_checkpoint": "Restore workflow state from a SimFlow checkpoint.",
    "project_reentry": "Start every project session here: open a context and return the forward-only experiment recovery summary.",
    "begin_experiment": "Begin a new forward-only tracked experiment without importing legacy history.",
    "finish_experiment": "Complete, fail, pause, or abandon a tracked experiment.",
    "begin_iteration": "Begin a loop iteration with explicit acceptance criteria.",
    "evaluate_iteration": "Evaluate an iteration and record its recovery point and next action.",
    "start_activity": "Record intent, method, scripts, command, inputs, and expected outputs before work starts.",
    "finish_activity": "Record activity outputs, outcome, failure, recovery point, and next action.",
    "experiment_timeline": "Query a paginated structured experiment history without reading host transcripts.",
    "fork_experiment": "Create a new experiment branch with explicit provenance parents.",
    "resume_experiment": "Resume a paused experiment without rewriting prior history.",
    "compare_experiments": "Compare status, metrics, failures, recovery points, and lineage across experiment branches.",
    "verify_experiment_ledger": "Verify SQLite integrity, immutable event hashes, and registered references.",
    "rebuild_experiment_exports": "Rebuild derived JSON, JSONL, and Markdown views from canonical SQLite state.",
    "migrate_experiment_ledger": "Explicitly migrate structured v1 ledger files without importing host transcripts.",
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
            "experiment_id": {"type": "string"},
            "scan_root": {"type": "string"},
            "write_report": {"type": "boolean", "default": False},
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
    "repair_state": {
        "type": "object",
        "required": ["project_root"],
        "properties": {
            "project_root": {"type": "string"},
            "mode": {"type": "string", "enum": ["audit", "apply"], "default": "audit"},
            "min_confidence": {"type": "number", "exclusiveMinimum": 0.8, "default": 0.81},
        },
        "additionalProperties": False,
    },
    "register_artifact": {
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
    "list_artifacts": {
        "type": "object",
        "required": ["project_root"],
        "properties": {
            "project_root": {"type": "string"},
            "stage": {"type": "string"},
        },
        "additionalProperties": False,
    },
    "get_artifact": {
        "type": "object",
        "required": ["project_root", "artifact_id"],
        "properties": {
            "project_root": {"type": "string"},
            "artifact_id": {"type": "string"},
        },
        "additionalProperties": False,
    },
    "create_checkpoint": {
        "type": "object",
        "required": ["project_root", "workflow_id", "stage_id"],
        "properties": {
            "project_root": {"type": "string"},
            "workflow_id": {"type": "string"},
            "stage_id": {"type": "string"},
            "description": {"type": "string"},
            "status": {"type": "string", "enum": ["success", "partial", "failure"]},
            "job_id": {"type": "string"},
        },
        "additionalProperties": False,
    },
    "list_checkpoints": {
        "type": "object",
        "required": ["project_root"],
        "properties": {"project_root": {"type": "string"}},
        "additionalProperties": False,
    },
    "restore_checkpoint": {
        "type": "object",
        "required": ["project_root", "checkpoint_id"],
        "properties": {
            "project_root": {"type": "string"},
            "checkpoint_id": {"type": "string"},
        },
        "additionalProperties": False,
    },
    "project_reentry": {
        "type": "object",
        "required": ["project_root"],
        "properties": {
            "project_root": {"type": "string"},
            "experiment_id": {"type": "string"},
            "working_directory": {"type": "string"},
            "recent_limit": {"type": "integer", "minimum": 1, "maximum": 50, "default": 10},
        },
        "additionalProperties": False,
    },
    "begin_experiment": {
        "type": "object",
        "required": ["project_root", "session_context_id", "title", "objective", "stage", "root_path"],
        "properties": {
            "project_root": {"type": "string"},
            "session_context_id": {"type": "string"},
            "title": {"type": "string"},
            "objective": {"type": "string"},
            "stage": {"type": "string"},
            "root_path": {"type": "string"},
            "recipe": {"type": "string"},
            "acceptance_criteria": {"type": "array", "items": {"type": ["string", "object"]}},
            "next_action": {"type": ["string", "object"]},
            "scientific_question": {"type": "string"},
            "hypothesis": {"type": "string"},
            "tags": {"type": "array", "items": {"type": "string"}},
            "parent_experiment_ids": {"type": "array", "items": {"type": "string"}},
            "baseline_refs": {"type": "array", "items": {"type": "object"}},
        },
        "additionalProperties": False,
    },
    "finish_experiment": {
        "type": "object",
        "required": ["project_root", "session_context_id", "experiment_id", "status"],
        "properties": {
            "project_root": {"type": "string"},
            "session_context_id": {"type": "string"},
            "experiment_id": {"type": "string"},
            "status": {"type": "string", "enum": ["paused", "completed", "failed", "abandoned"]},
            "conclusion": {"type": "string"},
            "next_action": {"type": ["string", "object"]},
        },
        "additionalProperties": False,
    },
    "begin_iteration": {
        "type": "object",
        "required": ["project_root", "session_context_id", "experiment_id", "objective", "acceptance_criteria"],
        "properties": {
            "project_root": {"type": "string"},
            "session_context_id": {"type": "string"},
            "experiment_id": {"type": "string"},
            "objective": {"type": "string"},
            "acceptance_criteria": {"type": "array", "items": {"type": ["string", "object"]}},
            "parent_iteration_id": {"type": "string"},
            "inputs": {"type": "array"},
            "next_action": {"type": ["string", "object"]},
        },
        "additionalProperties": False,
    },
    "evaluate_iteration": {
        "type": "object",
        "required": ["project_root", "session_context_id", "experiment_id", "iteration_id", "status", "decision"],
        "properties": {
            "project_root": {"type": "string"},
            "session_context_id": {"type": "string"},
            "experiment_id": {"type": "string"},
            "iteration_id": {"type": "string"},
            "status": {"type": "string", "enum": ["evaluating", "accepted", "rejected", "failed", "paused", "superseded"]},
            "criterion_results": {"type": "array", "items": {"type": "object"}},
            "decision": {"type": "string"},
            "next_action": {"type": ["string", "object"]},
            "recovery": {"type": "object"},
        },
        "additionalProperties": False,
    },
    "start_activity": {
        "type": "object",
        "required": ["project_root", "session_context_id", "experiment_id", "objective", "activity_type", "stage"],
        "properties": {
            "project_root": {"type": "string"},
            "session_context_id": {"type": "string"},
            "experiment_id": {"type": "string"},
            "iteration_id": {"type": "string"},
            "objective": {"type": "string"},
            "activity_type": {"type": "string"},
            "stage": {"type": "string"},
            "method": {"type": "string"},
            "software": {"type": "string"},
            "version": {"type": "string"},
            "scripts": {"type": "array", "items": {"type": "object"}},
            "command": {"type": "string"},
            "inputs": {"type": "array"},
            "parameters": {"type": "object"},
            "expected_outputs": {"type": "array"},
            "gate_ids": {"type": "array", "items": {"type": "string"}},
            "random_seeds": {"type": "array"},
            "environment_ref": {"type": "string"},
        },
        "additionalProperties": False,
    },
    "finish_activity": {
        "type": "object",
        "required": ["project_root", "session_context_id", "experiment_id", "activity_id", "status"],
        "properties": {
            "project_root": {"type": "string"},
            "session_context_id": {"type": "string"},
            "experiment_id": {"type": "string"},
            "activity_id": {"type": "string"},
            "status": {"type": "string", "enum": ["completed", "partial", "failed", "paused", "cancelled"]},
            "outputs": {"type": "array"},
            "artifact_ids": {"type": "array", "items": {"type": "string"}},
            "job_ids": {"type": "array", "items": {"type": "string"}},
            "checkpoint_id": {"type": "string"},
            "observations": {"type": "string"},
            "metrics": {"type": "object"},
            "failure": {"type": "object"},
            "restart_from": {"type": "object"},
            "next_action": {"type": ["string", "object"]},
        },
        "additionalProperties": False,
    },
    "experiment_timeline": {
        "type": "object",
        "required": ["project_root", "experiment_id"],
        "properties": {
            "project_root": {"type": "string"},
            "experiment_id": {"type": "string"},
            "iteration_id": {"type": "string"},
            "status": {"type": "string"},
            "offset": {"type": "integer", "minimum": 0, "default": 0},
            "limit": {"type": "integer", "minimum": 1, "maximum": 200, "default": 50},
        },
        "additionalProperties": False,
    },
    "fork_experiment": {
        "type": "object",
        "required": ["project_root", "session_context_id", "parent_experiment_id", "title", "objective", "root_path"],
        "properties": {
            "project_root": {"type": "string"},
            "session_context_id": {"type": "string"},
            "parent_experiment_id": {"type": "string"},
            "title": {"type": "string"},
            "objective": {"type": "string"},
            "root_path": {"type": "string"},
            "scientific_question": {"type": "string"},
            "hypothesis": {"type": "string"},
            "stage": {"type": "string"},
            "recipe": {"type": "string"},
            "acceptance_criteria": {"type": "array", "items": {"type": ["string", "object"]}},
            "baseline_refs": {"type": "array", "items": {"type": "object"}},
            "next_action": {"type": ["string", "object"]},
        },
        "additionalProperties": False,
    },
    "resume_experiment": {
        "type": "object",
        "required": ["project_root", "session_context_id", "experiment_id"],
        "properties": {
            "project_root": {"type": "string"},
            "session_context_id": {"type": "string"},
            "experiment_id": {"type": "string"},
            "next_action": {"type": ["string", "object"]},
        },
        "additionalProperties": False,
    },
    "compare_experiments": {
        "type": "object",
        "required": ["project_root", "experiment_ids"],
        "properties": {
            "project_root": {"type": "string"},
            "experiment_ids": {"type": "array", "items": {"type": "string"}, "minItems": 2, "maxItems": 10},
        },
        "additionalProperties": False,
    },
    "verify_experiment_ledger": {
        "type": "object",
        "required": ["project_root"],
        "properties": {
            "project_root": {"type": "string"},
            "verify_references": {"type": "boolean", "default": True},
        },
        "additionalProperties": False,
    },
    "rebuild_experiment_exports": {
        "type": "object",
        "required": ["project_root", "session_context_id", "experiment_id", "activity_id"],
        "properties": {
            "project_root": {"type": "string"},
            "session_context_id": {"type": "string"},
            "experiment_id": {"type": "string"},
            "iteration_id": {"type": "string"},
            "activity_id": {"type": "string"},
        },
        "additionalProperties": False,
    },
    "migrate_experiment_ledger": {
        "type": "object",
        "required": ["project_root", "confirm"],
        "properties": {
            "project_root": {"type": "string"},
            "confirm": {"type": "boolean"},
        },
        "additionalProperties": False,
    },
}


_LEDGER_LINKED_WRITES = {
    "write_state", "update_stage", "record_computation_evidence", "record_analysis_evidence",
    "record_user_override", "record_stage_failure", "register_artifact", "create_checkpoint",
    "restore_checkpoint",
    "rebuild_experiment_exports",
}

for _tool_name in _LEDGER_LINKED_WRITES:
    _schema = TOOL_SCHEMAS[_tool_name]
    _schema["properties"].update({
        "session_context_id": {"type": "string"},
        "experiment_id": {"type": "string"},
        "activity_id": {"type": "string"},
        "iteration_id": {"type": "string"},
    })

TOOL_SCHEMAS["session_handoff"]["properties"].update({
    "session_context_id": {"type": "string"},
    "experiment_id": {"type": "string"},
    "note": {"type": "string"},
})


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
    write_context = None

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
        if tool == "repair_state":
            full_tool_name += f".{str(params.get('mode', 'audit')).strip().lower()}"
        repair_audit = full_tool_name == "simflow_state/repair_state.audit"

        from runtime.simflow_core.experiment_memory import (
            is_ledger_enabled,
            require_write_context,
            validate_session_context,
        )

        if is_ledger_enabled(project_root):
            if tool in _LEDGER_LINKED_WRITES and not repair_audit:
                missing_context = [
                    field for field in ("session_context_id", "experiment_id", "activity_id")
                    if not params.get(field)
                ]
                if missing_context:
                    return {
                        "status": "error",
                        "code": "experiment_context_required",
                        "message": (
                            "The forward-only experiment ledger is enabled. Call project_reentry and "
                            "start_activity, then provide session_context_id, experiment_id, and activity_id."
                        ),
                        "missing": missing_context,
                    }
                try:
                    write_context = require_write_context(
                        project_root,
                        session_context_id=params["session_context_id"],
                        experiment_id=params["experiment_id"],
                        activity_id=params["activity_id"],
                        iteration_id=params.get("iteration_id"),
                    )
                except ValueError as error:
                    return {"status": "error", "code": "invalid_experiment_context", "message": str(error)}
            elif tool == "session_handoff":
                try:
                    validate_session_context(project_root, params.get("session_context_id", ""))
                except ValueError as error:
                    return {"status": "error", "code": "invalid_experiment_context", "message": str(error)}

        # P3.1: Auto-read_state for first-call to read-only tools
        # If no prior session exists and this is a read-only tool (not read_state
        # itself, not a state-write tool), auto-record read_state to bootstrap
        # the session. This satisfies the prerequisite for future state-write calls.
        if full_tool_name in EXEMPT_TOOLS and tool not in ("read_state", "init_workflow", "repair_state"):
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
        if not repair_audit:
            record_tool_call(full_tool_name, project_root)

    try:
        from runtime.simflow_core.experiment_memory import experiment_write_scope
        with experiment_write_scope(write_context):
            return TOOLS[tool](params)
    except Exception as e:
        return {"status": "error", "message": str(e)}


if __name__ == "__main__":
    run_mcp_server("simflow_state", TOOLS, TOOL_DESCRIPTIONS, TOOL_SCHEMAS, request_handler=handle_request)
