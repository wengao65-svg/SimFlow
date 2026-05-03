"""Verification gate engine for SimFlow workflows.

Loads gate definitions from workflow/gates/ and evaluates conditions
against a runtime context. Gates enforce approval workflows at critical
stage transitions (e.g., HPC submit, convergence acceptance).
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

GATES_DIR = Path(__file__).parent.parent.parent / "workflow" / "gates"
GATE_STATE_FILE = ".simflow/state/gates.json"


def list_gates() -> List[str]:
    """List all available gate names."""
    return sorted(p.stem for p in GATES_DIR.glob("*.json"))


def load_gate(gate_name: str) -> dict:
    """Load a gate definition by name.

    Args:
        gate_name: Gate name (filename without .json)

    Returns:
        Gate definition dict

    Raises:
        FileNotFoundError: If gate definition not found
    """
    path = GATES_DIR / f"{gate_name}.json"
    if not path.exists():
        raise FileNotFoundError(f"Gate definition not found: {gate_name}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def evaluate_conditions(gate: dict, context: Dict[str, Any]) -> dict:
    """Evaluate gate conditions against a runtime context.

    Args:
        gate: Gate definition dict
        context: Dict mapping condition names to boolean-like values.
                 Conditions are considered met if context[name] is truthy.

    Returns:
        Dict with keys: all_met (bool), met (list), unmet (list)
    """
    conditions = gate.get("conditions", [])
    met = []
    unmet = []
    for cond in conditions:
        if context.get(cond):
            met.append(cond)
        else:
            unmet.append(cond)
    return {
        "all_met": len(unmet) == 0,
        "met": met,
        "unmet": unmet,
    }


def check_gate(gate_name: str, context: Dict[str, Any]) -> dict:
    """Check a gate: evaluate conditions and return structured result.

    Args:
        gate_name: Gate name
        context: Dict mapping condition names to boolean-like values

    Returns:
        Dict with keys:
            - gate: gate name
            - status: "pass" if all conditions met, "block" otherwise
            - conditions: {all_met, met, unmet}
            - actions_on_approve: list (available when status is "pass")
            - actions_on_reject: list (available when status is "block")
            - auto_approve: bool
            - description: gate description
    """
    gate = load_gate(gate_name)
    cond_result = evaluate_conditions(gate, context)

    result = {
        "gate": gate_name,
        "description": gate.get("description", ""),
        "conditions": cond_result,
        "auto_approve": gate.get("auto_approve", False),
    }

    if cond_result["all_met"]:
        result["status"] = "pass"
        result["actions_on_approve"] = gate.get("actions_on_approve", [])
    else:
        result["status"] = "block"
        result["actions_on_reject"] = gate.get("actions_on_reject", [])

    # Include thresholds if present
    if "thresholds" in gate:
        result["thresholds"] = gate["thresholds"]

    return result


def record_gate_decision(
    gate_name: str,
    decision: str,
    context: Dict[str, Any],
    base_dir: str = ".",
    agent: str = "",
) -> dict:
    """Record a gate approval/rejection decision.

    Args:
        gate_name: Gate name
        decision: "approved" or "rejected"
        context: The conditions context used for evaluation
        base_dir: Base directory for state persistence
        agent: Agent/user making the decision

    Returns:
        The recorded decision record
    """
    record = {
        "gate": gate_name,
        "decision": decision,
        "conditions": context,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "agent": agent,
    }

    path = Path(base_dir) / GATE_STATE_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = []
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            existing = json.load(f)
    existing.append(record)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=2, ensure_ascii=False)

    return record


def get_gate_decisions(
    gate_name: Optional[str] = None,
    base_dir: str = ".",
) -> list:
    """Get recorded gate decisions, optionally filtered by gate name.

    Args:
        gate_name: Filter by gate name, or None for all
        base_dir: Base directory

    Returns:
        List of decision records
    """
    path = Path(base_dir) / GATE_STATE_FILE
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        decisions = json.load(f)
    if gate_name:
        return [d for d in decisions if d.get("gate") == gate_name]
    return decisions
