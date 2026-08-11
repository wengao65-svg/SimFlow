"""Tool: Record a user-approved gate bypass/override decision.

This tool allows users to explicitly record that they bypassed a safety
gate (e.g., high-temperature gate, high-T Li-Li distance gate). The
override is written to gates.json with decision='user_override' so the
workflow layer has visibility into bypass decisions.

This is the SimFlow-native alternative to users creating local
gate_decision.json files in work directories that SimFlow cannot see.
"""

import json
from datetime import datetime, timezone

from runtime.simflow_core.state import ProjectRootError, read_state, resolve_project_root, write_state, touch_workflow


def _project_root(params: dict) -> str:
    project_root = params.get("project_root")
    if not project_root:
        raise ProjectRootError("project_root is required for MCP write operations")
    return project_root


def execute(params: dict) -> dict:
    """Record a user-approved gate bypass/override in gates.json.

    Required params:
    - project_root: The project root path
    - gate_id: A stable identifier for this override (e.g., 'override_001_no_high_t_gate')
    - approver_context: Who approved the bypass and why (free text)
    - risk_note: Description of the risk being accepted

    Optional params:
    - original_gate_failure_ref: Reference to the original gate that failed
      (e.g., checkpoint_id or gate_decision_id)
    - requested_action: What action the override enables
    - directory_path: The directory where the bypassed work happens
    """
    try:
        project_root = _project_root(params)
        root = resolve_project_root(project_root=project_root)
    except ProjectRootError as error:
        return {"status": "error", "message": str(error)}

    gate_id = params.get("gate_id")
    approver_context = params.get("approver_context")
    risk_note = params.get("risk_note")

    if not gate_id:
        return {"status": "error", "message": "gate_id is required"}
    if not approver_context:
        return {"status": "error", "message": "approver_context is required"}
    if not risk_note:
        return {"status": "error", "message": "risk_note is required"}

    now = datetime.now(timezone.utc).isoformat()
    from runtime.simflow_core.experiment_memory import record_linked_write, require_write_context

    ledger_context = require_write_context(
        str(root),
        session_context_id=params.get("session_context_id"),
        experiment_id=params.get("experiment_id"),
        iteration_id=params.get("iteration_id"),
        activity_id=params.get("activity_id"),
    )
    context_kwargs = {
        "session_context_id": ledger_context.session_context_id if ledger_context else None,
        "experiment_id": ledger_context.experiment_id if ledger_context else None,
        "iteration_id": ledger_context.iteration_id if ledger_context else None,
        "activity_id": ledger_context.activity_id if ledger_context else None,
    }

    override_entry = {
        "gate_id": gate_id,
        "stage": params.get("stage", "computation"),
        "decision": "user_override",
        "approver_context": approver_context,
        "risk_note": risk_note,
        "requested_action": params.get("requested_action", ""),
        "directory_path": params.get("directory_path", ""),
        "original_gate_failure_ref": params.get("original_gate_failure_ref", ""),
        "experiment_id": context_kwargs["experiment_id"],
        "iteration_id": context_kwargs["iteration_id"],
        "activity_id": context_kwargs["activity_id"],
        "created_at": now,
    }

    # Read existing gates and append
    gates = read_state(project_root=str(root), state_file="gates.json")
    if not isinstance(gates, list):
        gates = []

    # Check for duplicate gate_id
    existing_ids = {g.get("gate_id") for g in gates if isinstance(g, dict)}
    if gate_id in existing_ids:
        return {
            "status": "error",
            "message": f"gate_id '{gate_id}' already exists in gates.json",
            "code": "duplicate_gate_id",
        }

    gates.append(override_entry)
    write_state(gates, project_root=str(root), state_file="gates.json", **context_kwargs)
    touch_workflow(str(root), **context_kwargs)
    record_linked_write(
        str(root),
        kind="gate",
        target_id=gate_id,
        role="user_override",
        metadata={"decision": "user_override", "stage": override_entry["stage"]},
        **context_kwargs,
    )

    return {
        "status": "success",
        "project_root": str(root),
        "data": {
            "gate_id": gate_id,
            "decision": "user_override",
            "recorded_at": now,
            "total_gates": len(gates),
        },
    }
