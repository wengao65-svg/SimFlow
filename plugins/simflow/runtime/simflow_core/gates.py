"""Verification gate engine for SimFlow workflows.

Loads gate definitions from workflow/gates/ and evaluates conditions against
recorded JSON evidence. Gates enforce approval workflows at critical stage
transitions (e.g., HPC submit, convergence acceptance) without trusting
boolean-only runtime context.
"""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .records import list_project_records, record_event
from .state import resolve_project_root

GATES_DIR = Path(__file__).parent.parent.parent / "workflow" / "gates"
GATE_STATE_FILE = ".simflow/state/gates.json"
RUNTIME_OWNED_GATES = {"hpc_submit", "hpc_transfer"}


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
    if evidence == "state/gates.json":
        return build_gate_state(project_root=str(project_root)), project_root / ".simflow" / "records.jsonl", None
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
        context: Runtime context containing project_root/base_dir. Conditions
                 read JSON artifacts from project_root/.simflow/ rather than
                 trusting boolean flags.

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
            detail = {
                "id": str(cond),
                "kind": "unsupported",
                "met": False,
                "error": "legacy_context_condition_not_supported",
            }
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
        context: Dict containing project_root/base_dir for evidence lookup.

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
    if gate_name in RUNTIME_OWNED_GATES:
        return {
            "gate": gate_name,
            "description": gate.get("description", ""),
            "status": "block",
            "runtime_owned": True,
            "conditions": {
                "all_met": False,
                "met": [],
                "unmet": ["public_hpc_runtime_required"],
                "details": [{
                    "id": "public_hpc_runtime_required",
                    "kind": "runtime_boundary",
                    "met": False,
                    "error": "Use hpc/plan and approval bound to run_plan_hash; this advisory gate cannot authorize execution.",
                }],
            },
            "auto_approve": False,
            "actions_on_reject": gate.get("actions_on_reject", []),
        }
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
    root = resolve_project_root(project_root=project_root, base_dir=base_dir)
    record = {
        "decision_id": decision_id,
        "gate": gate_name,
        "decision": decision,
        "conditions": context,
        "timestamp": now,
        "agent": agent,
    }

    binding = None
    run_plan_hash = context.get("run_plan_hash") if isinstance(context, dict) else None
    if run_plan_hash:
        from .run_bindings import get_run_plan_binding

        binding = get_run_plan_binding(str(root), str(run_plan_hash))

    record_event(
        str(root),
        kind="approval",
        summary=f"{gate_name}: {decision}",
        status=decision,
        details={
            "decision_id": decision_id,
            "gate": gate_name,
            "conditions": context,
            "agent": agent,
        },
        record_id=decision_id,
        experiment_id=(binding or {}).get("experiment_id"),
        attempt_id=(binding or {}).get("attempt_id"),
    )

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
    try:
        payload = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else []
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        payload = []
    legacy = payload.get("decisions", []) if isinstance(payload, dict) else payload
    decisions = [item for item in legacy if isinstance(item, dict)] if isinstance(legacy, list) else []
    seen = {item.get("decision_id") or item.get("gate_id") for item in decisions}
    for item in list_project_records(str(root), kind="approval"):
        details = item.get("details") if isinstance(item.get("details"), dict) else {}
        decision_id = details.get("decision_id") or item.get("record_id")
        if decision_id in seen:
            continue
        decisions.append({
            "decision_id": decision_id,
            "gate": details.get("gate"),
            "decision": item.get("status"),
            "conditions": details.get("conditions") or {},
            "timestamp": item.get("created_at"),
            "agent": details.get("agent", ""),
            "storage": "compact_record",
        })
        seen.add(decision_id)
    if gate_name:
        return [d for d in decisions if d.get("gate") == gate_name]
    return decisions


def build_gate_state(base_dir: str = ".", project_root: Optional[str] = None) -> Any:
    """Return a compatibility view without rewriting legacy gates.json."""
    root = resolve_project_root(project_root=project_root, base_dir=base_dir)
    path = root / GATE_STATE_FILE
    try:
        legacy = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else []
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        legacy = []
    compact_records = list_project_records(str(root), kind="approval")
    if not compact_records:
        return legacy
    decisions = get_gate_decisions(base_dir=str(root), project_root=str(root))
    state: dict[str, Any] = {"decisions": decisions}
    for item in decisions:
        gate_name = item.get("gate")
        if not gate_name:
            continue
        state[gate_name] = {
            "latest_decision": item.get("decision"),
            "latest_decision_id": item.get("decision_id") or item.get("gate_id"),
            "latest_decision_at": item.get("timestamp"),
            "latest_agent": item.get("agent", ""),
        }
    return state
