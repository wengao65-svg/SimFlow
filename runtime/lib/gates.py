"""Verification gate engine for SimFlow workflows.

Loads gate definitions from workflow/gates/ and evaluates conditions
against a runtime context. Gates enforce approval workflows at critical
stage transitions (e.g., HPC submit, convergence acceptance).
"""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .state import resolve_project_root

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


def _condition_id(condition: Any) -> str:
    if isinstance(condition, dict):
        return str(condition.get("id") or condition.get("name") or condition.get("evidence") or "condition")
    return str(condition)


def _project_root_from_context(context: Dict[str, Any]) -> Path:
    return resolve_project_root(
        project_root=context.get("project_root"),
        base_dir=context.get("base_dir", "."),
    )


def _candidate_evidence_paths(project_root: Path, evidence: str) -> list[Path]:
    evidence_path = Path(evidence).expanduser()
    if evidence_path.is_absolute():
        return [evidence_path]

    candidates = [
        project_root / evidence_path,
        project_root / ".simflow" / evidence_path,
        project_root / ".simflow" / "artifacts" / evidence_path,
    ]
    seen: set[Path] = set()
    unique = []
    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved not in seen:
            seen.add(resolved)
            unique.append(resolved)
    return unique


def _load_evidence(project_root: Path, evidence: str) -> tuple[Any, Optional[Path], Optional[str]]:
    for path in _candidate_evidence_paths(project_root, evidence):
        if not path.exists():
            continue
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f), path, None
        except json.JSONDecodeError as exc:
            return None, path, f"invalid_json: {exc}"
    candidates = [str(path) for path in _candidate_evidence_paths(project_root, evidence)]
    return None, None, f"missing_evidence: tried {candidates}"


def _read_json_path(payload: Any, path: str) -> tuple[Any, Optional[str]]:
    if path in ("", "$"):
        return payload, None
    if not path.startswith("$."):
        return None, f"unsupported_path: {path}"

    current = payload
    for part in path[2:].split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
            continue
        if isinstance(current, list) and part.isdigit():
            index = int(part)
            if 0 <= index < len(current):
                current = current[index]
                continue
        return None, f"missing_path: {path}"
    return current, None


def _evaluate_op(actual: Any, op: str, expected: Any) -> bool:
    if op == "eq":
        return actual == expected
    if op == "neq":
        return actual != expected
    if op == "in":
        return isinstance(expected, list) and actual in expected
    if op == "length_eq":
        try:
            return len(actual) == expected
        except TypeError:
            return False
    if op == "exists":
        return actual is not None if expected is None else (actual is not None) == bool(expected)
    if op == "truthy":
        return bool(actual)
    if op == "falsy":
        return not bool(actual)
    raise ValueError(f"Unsupported gate condition op: {op}")


def _evaluate_legacy_condition(condition: str, context: Dict[str, Any]) -> dict:
    met = bool(context.get(condition))
    return {
        "id": condition,
        "kind": "context",
        "met": met,
        "actual": context.get(condition),
    }


def _evaluate_evidence_condition(condition: dict, context: Dict[str, Any]) -> dict:
    cond_id = _condition_id(condition)
    evidence = condition.get("evidence")
    path = condition.get("path", "$")
    op = condition.get("op", "eq")
    expected = condition.get("value")

    detail = {
        "id": cond_id,
        "kind": "evidence",
        "evidence": evidence,
        "path": path,
        "op": op,
        "expected": expected,
        "met": False,
    }
    if not evidence:
        detail["error"] = "missing_condition_evidence"
        return detail

    try:
        project_root = _project_root_from_context(context)
        payload, evidence_path, load_error = _load_evidence(project_root, str(evidence))
        if evidence_path is not None:
            detail["evidence_path"] = str(evidence_path)
        if load_error:
            detail["error"] = load_error
            return detail

        actual, path_error = _read_json_path(payload, str(path))
        if path_error:
            detail["error"] = path_error
            return detail
        detail["actual"] = actual
        detail["met"] = _evaluate_op(actual, str(op), expected)
        if not detail["met"]:
            detail["error"] = "condition_not_met"
        return detail
    except Exception as exc:  # pragma: no cover - defensive detail for gate reports
        detail["error"] = str(exc)
        return detail


def evaluate_conditions(gate: dict, context: Dict[str, Any]) -> dict:
    """Evaluate gate conditions against a runtime context.

    Args:
        gate: Gate definition dict
        context: Runtime context. Legacy string conditions read boolean-like
                 values from this dict. Evidence conditions read JSON artifacts
                 from project_root/.simflow/ rather than trusting booleans.

    Returns:
        Dict with keys: all_met (bool), met (list), unmet (list), details (list)
    """
    conditions = gate.get("conditions", [])
    met = []
    unmet = []
    details = []
    for cond in conditions:
        if isinstance(cond, dict):
            detail = _evaluate_evidence_condition(cond, context)
        else:
            detail = _evaluate_legacy_condition(str(cond), context)
        cond_id = detail["id"]
        details.append(detail)
        if detail["met"]:
            met.append(cond_id)
        else:
            unmet.append(cond_id)
    return {
        "all_met": len(unmet) == 0,
        "met": met,
        "unmet": unmet,
        "details": details,
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
    project_root: Optional[str] = None,
) -> dict:
    """Record a gate approval/rejection decision.

    Args:
        gate_name: Gate name
        decision: "approved" or "rejected"
        context: The conditions context used for evaluation
        base_dir: Base directory for state persistence
        agent: Agent/user making the decision
        project_root: Explicit project root for .simflow state

    Returns:
        The recorded decision record
    """
    now = datetime.now(timezone.utc).isoformat()
    decision_id = f"gate_decision_{uuid.uuid4().hex[:12]}"
    record = {
        "decision_id": decision_id,
        "gate": gate_name,
        "decision": decision,
        "conditions": context,
        "timestamp": now,
        "agent": agent,
    }

    root = resolve_project_root(project_root=project_root, base_dir=base_dir)
    path = root / GATE_STATE_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    existing: Any = {"decisions": []}
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            existing = json.load(f)
    if isinstance(existing, list):
        existing = {"decisions": existing}
    if not isinstance(existing, dict):
        existing = {"decisions": []}
    existing.setdefault("decisions", [])
    existing["decisions"].append(record)
    existing[gate_name] = {
        "latest_decision": decision,
        "latest_decision_id": decision_id,
        "latest_decision_at": now,
        "latest_agent": agent,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=2, ensure_ascii=False)

    return record


def get_gate_decisions(
    gate_name: Optional[str] = None,
    base_dir: str = ".",
    project_root: Optional[str] = None,
) -> list:
    """Get recorded gate decisions, optionally filtered by gate name.

    Args:
        gate_name: Filter by gate name, or None for all
        base_dir: Base directory
        project_root: Explicit project root for .simflow state

    Returns:
        List of decision records
    """
    root = resolve_project_root(project_root=project_root, base_dir=base_dir)
    path = root / GATE_STATE_FILE
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        payload = json.load(f)
    decisions = payload.get("decisions", []) if isinstance(payload, dict) else payload
    if gate_name:
        return [d for d in decisions if d.get("gate") == gate_name]
    return decisions
