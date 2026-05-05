"""VASP task orchestration helpers for SimFlow."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .artifact import register_artifact
from .checkpoint import create_checkpoint
from .gates import check_gate
from .hpc import estimate_resources
from .state import ensure_simflow_dir, read_state, update_stage, write_state
from .vasp_py4vasp import can_use_py4vasp, read_with_py4vasp
from .vasp_tools import detect_vaspkit, plan_vaspkit_task
from .vasp_validation import validate_vasp_inputs


TASK_ALIASES = {
    "relaxation": "relax",
    "geometry optimization": "relax",
    "static": "static",
    "scf": "static",
    "single point": "static",
    "dos": "dos",
    "density of states": "dos",
    "band": "band",
    "bands": "band",
    "band structure": "band",
    "aimd": "aimd",
    "md": "aimd",
    "neb": "neb_basic",
    "surface": "surface_check",
    "adsorption": "adsorption_check",
    "defect": "defect_check",
    "parse": "parse",
    "troubleshoot": "troubleshoot",
}

TASK_INPUTS = {
    "relax": ["POSCAR", "INCAR", "KPOINTS", "POTCAR"],
    "static": ["POSCAR", "INCAR", "KPOINTS", "POTCAR"],
    "dos": ["POSCAR", "INCAR", "KPOINTS", "POTCAR", "CHGCAR"],
    "band": ["POSCAR", "INCAR", "KPOINTS", "POTCAR", "CHGCAR"],
    "aimd": ["POSCAR", "INCAR", "KPOINTS", "POTCAR"],
    "neb_basic": ["INCAR", "KPOINTS", "POTCAR"],
    "surface_check": ["POSCAR"],
    "adsorption_check": ["POSCAR"],
    "defect_check": ["POSCAR"],
    "parse": [],
    "troubleshoot": [],
}

TASK_PREDECESSORS = {
    "dos": ["static SCF with CHGCAR"],
    "band": ["static SCF with CHGCAR", "line-mode KPOINTS"],
    "neb_basic": ["initial/final structures and image directories 00, 01, ..."],
}


def classify_vasp_request(request: str, files: list[str] | None = None) -> dict[str, Any]:
    """Classify a user request into a common VASP task."""
    text = request.lower()
    task = "static"
    for phrase, candidate in sorted(TASK_ALIASES.items(), key=lambda item: len(item[0]), reverse=True):
        if phrase in text:
            task = candidate
            break

    available = {Path(f).name for f in (files or [])}
    required = TASK_INPUTS.get(task, [])
    missing = [name for name in required if name not in available]
    tools = ["SimFlow templates/runtime/parsers"]
    if task in {"dos", "band", "surface_check", "adsorption_check", "defect_check"}:
        tools.append("VASPKIT if available")
    if task in {"parse", "dos", "band", "aimd"}:
        tools.append("py4vasp if vaspout.h5 exists")

    return {
        "task": task,
        "required_inputs": required,
        "available_inputs": sorted(available),
        "missing_inputs": missing,
        "predecessors": TASK_PREDECESSORS.get(task, []),
        "recommended_tools": tools,
    }


def _write_json(base_dir: Path, relative_path: str, data: dict[str, Any]) -> str:
    path = base_dir / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return relative_path


def _analysis_report(task: str, calc_dir: Path) -> dict[str, Any]:
    py4 = can_use_py4vasp(str(calc_dir))
    if py4["usable"]:
        result = read_with_py4vasp(str(calc_dir), "summary")
        return {"backend": "py4vasp", "status": result.get("status"), "result": result}

    fallback_files = [name for name in ("vasprun.xml", "OUTCAR", "OSZICAR", "EIGENVAL") if (calc_dir / name).is_file()]
    return {
        "backend": "simflow_fallback",
        "status": "ready" if fallback_files else "missing_outputs",
        "fallback_files": fallback_files,
        "reason": py4["reason"],
    }


def build_vasp_task_plan(task: str, base_dir: str, options: dict[str, Any] | None = None) -> dict[str, Any]:
    """Build a complete dry-run VASP orchestration plan."""
    options = options or {}
    root = Path(base_dir)
    calc_dir = root / options.get("calc_dir", ".")
    files = [p.name for p in calc_dir.iterdir()] if calc_dir.exists() else []
    classification = classify_vasp_request(task, files)
    task_name = options.get("task") or classification["task"]
    validation = validate_vasp_inputs(task_name, str(calc_dir)) if task_name != "parse" else {"status": "skip", "checks": []}
    num_atoms = options.get("num_atoms", 1)
    num_kpoints = options.get("num_kpoints", 1)
    resources = estimate_resources("vasp", "md" if task_name == "aimd" else task_name, num_atoms, num_kpoints)
    gate_context = {
        "dry_run_passed": True,
        "input_files_complete": validation.get("status") in {"pass", "skip"},
        "resource_request_reasonable": resources["estimated_walltime_hours"] <= options.get("max_walltime_hours", 240),
        "no_credential_in_files": True,
    }
    compute_plan = {
        "software": "vasp",
        "task": task_name,
        "dry_run": True,
        "real_submit": False,
        "resources": resources,
        "hpc_submit_gate": check_gate("hpc_submit", gate_context),
    }
    return {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "task": task_name,
        "classification": classification,
        "calc_dir": str(calc_dir),
        "tools": {
            "vaspkit": detect_vaspkit(),
            "py4vasp": can_use_py4vasp(str(calc_dir)),
            "vaspkit_plan": plan_vaspkit_task(task_name if task_name in {"band", "dos"} else "structure_summary", str(calc_dir)),
        },
        "validation_report": validation,
        "compute_plan": compute_plan,
        "analysis_report": _analysis_report(task_name, calc_dir),
    }


def write_vasp_artifacts(plan: dict[str, Any], base_dir: str, workflow_id: str | None = None) -> dict[str, Any]:
    """Write VASP reports and register them as SimFlow artifacts."""
    root = Path(base_dir)
    ensure_simflow_dir(str(root))
    state = read_state(str(root))
    workflow_id = workflow_id or state.get("workflow_id", "wf_vasp")
    stage = "input_generation"

    manifest = {
        "task": plan["task"],
        "required_inputs": plan["classification"]["required_inputs"],
        "missing_inputs": plan["classification"]["missing_inputs"],
        "recommended_tools": plan["classification"]["recommended_tools"],
    }
    handoff = {
        "task": plan["task"],
        "artifacts": [
            "reports/vasp/input_manifest.json",
            "reports/vasp/validation_report.json",
            "reports/vasp/compute_plan.json",
            "reports/vasp/analysis_report.json",
        ],
        "next_steps": plan["classification"]["predecessors"] or ["Review validation report and run dry-run compute plan"],
        "approval_needed": plan["compute_plan"]["hpc_submit_gate"]["status"] != "pass",
    }
    files = {
        "input_manifest": _write_json(root, "reports/vasp/input_manifest.json", manifest),
        "validation_report": _write_json(root, "reports/vasp/validation_report.json", plan["validation_report"]),
        "compute_plan": _write_json(root, "reports/vasp/compute_plan.json", plan["compute_plan"]),
        "analysis_report": _write_json(root, "reports/vasp/analysis_report.json", plan["analysis_report"]),
        "handoff_artifact": _write_json(root, "reports/vasp/handoff_artifact.json", handoff),
    }

    artifacts = []
    for name, rel_path in files.items():
        artifacts.append(register_artifact(
            name=name,
            artifact_type="report" if name != "handoff_artifact" else "handoff",
            stage=stage,
            base_dir=str(root),
            path=rel_path,
            parameters={"task": plan["task"]},
            software="vasp",
        ))

    checkpoint = create_checkpoint(
        workflow_id=workflow_id,
        stage_id=stage,
        description=f"VASP {plan['task']} orchestration reports written",
        base_dir=str(root),
        status="success" if plan["validation_report"].get("status") in {"pass", "skip"} else "failed",
    )
    update_stage(stage, "completed", str(root), outputs=list(files.values()), checkpoint_id=checkpoint["checkpoint_id"])
    write_state({"latest_vasp_task": plan["task"], "latest_checkpoint": checkpoint["checkpoint_id"]}, str(root), "vasp.json")

    return {"files": files, "artifacts": artifacts, "checkpoint": checkpoint}
