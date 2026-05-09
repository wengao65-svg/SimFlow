"""CP2K workflow classification and dry-run planning for SimFlow."""

from __future__ import annotations

import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .cp2k_input import read_cif_to_xyz, read_xyz_structure
from .cp2k_validation import normalize_cp2k_task, validate_cp2k_inputs
from .gates import check_gate
from .state import resolve_project_root


TASK_ALIASES = {
    "single point": "energy",
    "single-point": "energy",
    "static energy": "energy",
    "energy": "energy",
    "geo opt": "geo_opt",
    "geometry optimization": "geo_opt",
    "geometry opt": "geo_opt",
    "relax": "geo_opt",
    "cell opt": "cell_opt",
    "cell optimization": "cell_opt",
    "nvt": "aimd_nvt",
    "nve": "aimd_nve",
    "npt": "aimd_npt",
    "aimd nvt": "aimd_nvt",
    "aimd nve": "aimd_nve",
    "aimd npt": "aimd_npt",
    "restart": "restart",
    "continue": "restart",
    "continuation": "restart",
    "parse": "parse",
    "parser": "parse",
    "troubleshoot": "troubleshoot",
    "convergence": "troubleshoot",
}

TASK_REQUIREMENTS = {
    "energy": ["cp2k_input", "coordinates"],
    "geo_opt": ["cp2k_input", "coordinates"],
    "cell_opt": ["cp2k_input", "coordinates"],
    "aimd_nvt": ["cp2k_input", "coordinates"],
    "aimd_nve": ["cp2k_input", "coordinates"],
    "aimd_npt": ["cp2k_input", "coordinates"],
    "restart": ["cp2k_input", "coordinates", "restart_file"],
    "parse": ["cp2k_log"],
    "troubleshoot": ["cp2k_log"],
}

TASK_PREDECESSORS = {
    "restart": ["Existing CP2K restart artifact from a prior run"],
    "parse": ["Completed or partially completed CP2K output files"],
    "troubleshoot": ["CP2K log and any available energy/trajectory/restart files"],
}

REPORT_ARTIFACTS = [
    "reports/cp2k/input_manifest.json",
    "reports/cp2k/validation_report.json",
    "reports/cp2k/compute_plan.json",
    "reports/cp2k/analysis_report.json",
    "reports/cp2k/handoff_artifact.json",
]


def classify_cp2k_request(
    request: str,
    files: list[str] | None = None,
    options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Classify a request into a common CP2K task and file inventory."""
    options = options or {}
    file_inventory = _inventory(files or [])
    task = _classify_task(request, file_inventory)
    required = TASK_REQUIREMENTS[task]
    available = _available_labels(file_inventory)
    missing = [item for item in required if item not in available]

    tools = ["runtime.lib.cp2k_validation"]
    if task in {"energy", "geo_opt", "cell_opt", "aimd_nvt", "aimd_nve", "aimd_npt", "restart"}:
        tools.insert(0, "runtime.lib.cp2k_input")
    if task in {"restart", "parse", "troubleshoot"} or file_inventory["log_files"]:
        tools.append("runtime.lib.parsers.cp2k_parser")
    tools.append("SimFlow artifact/checkpoint writers")

    return {
        "task": task,
        "required_inputs": required,
        "available_inputs": sorted(available),
        "missing_inputs": missing,
        "recommended_tools": tools,
        "predecessors": TASK_PREDECESSORS.get(task, []),
        "file_inventory": file_inventory,
        "expected_artifacts": REPORT_ARTIFACTS,
        "options": options,
    }


def build_cp2k_task_plan(
    task: str,
    base_dir: str,
    options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a dry-run orchestration plan for a common CP2K task."""
    options = options or {}
    root = resolve_project_root(project_root=base_dir)
    calc_dir = root / options.get("calc_dir", ".")
    files = [path.name for path in calc_dir.iterdir()] if calc_dir.exists() else []
    classification = classify_cp2k_request(task, files, options)

    input_path = options.get("input_path")
    if input_path and not Path(input_path).is_absolute():
        input_path = str(calc_dir / input_path)

    validation = validate_cp2k_inputs(
        classification["task"],
        str(calc_dir),
        input_path=input_path,
    )
    runtime_detection = discover_cp2k_runtime()
    atom_count = _estimate_atom_count(calc_dir, classification["file_inventory"])
    resources = _estimate_cp2k_resources(classification["task"], atom_count)
    preferred_input = _preferred_input_name(calc_dir, input_path)
    recommended_executable = (
        runtime_detection["executables"][0]["executable"]
        if runtime_detection["executables"]
        else "cp2k.psmp"
    )
    command = f"{recommended_executable} -i {preferred_input} -o cp2k.log"
    gate_context = {
        "dry_run_passed": True,
        "input_files_complete": validation["status"] in {"pass", "skip"},
        "resource_request_reasonable": resources["estimated_walltime_hours"] <= options.get("max_walltime_hours", 240),
        "no_credential_in_files": True,
    }
    compute_plan = {
        "software": "cp2k",
        "task": classification["task"],
        "dry_run": True,
        "prepare_only": True,
        "real_submit": False,
        "approval_required_for_real_submit": True,
        "recommended_command": command,
        "resources": resources,
        "runtime_detection": runtime_detection,
        "steps": [
            "Review validation_report.json and missing inputs.",
            "Prepare or update the CP2K input deck and referenced coordinate/restart files.",
            "Use the dry-run command only after the approval gate is satisfied for any real submission.",
        ],
        "hpc_submit_gate": check_gate("hpc_submit", gate_context),
    }

    return {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "task": classification["task"],
        "calc_dir": str(calc_dir),
        "classification": classification,
        "validation_report": validation,
        "compute_plan": compute_plan,
        "expected_artifacts": REPORT_ARTIFACTS,
    }


def discover_cp2k_runtime() -> dict[str, Any]:
    """Detect CP2K executables available in the local environment."""
    executables = []
    for executable in ("cp2k.psmp", "cp2k.popt", "cp2k.sopt", "cp2k"):
        path = shutil.which(executable)
        if not path:
            continue
        executables.append({
            "executable": executable,
            "version": _read_cp2k_version(executable),
        })
    return {
        "detected": bool(executables),
        "executables": executables,
    }


def _classify_task(request: str, inventory: dict[str, list[str]]) -> str:
    try:
        return normalize_cp2k_task(request)
    except ValueError:
        pass

    text = request.lower().replace("_", " ")
    for phrase, task in sorted(TASK_ALIASES.items(), key=lambda item: len(item[0]), reverse=True):
        if phrase in text:
            return normalize_cp2k_task(task)

    if inventory["log_files"] and not inventory["input_files"]:
        return "parse"
    if inventory["restart_files"]:
        return "restart"
    return "energy"


def _inventory(files: list[str]) -> dict[str, list[str]]:
    input_files = []
    log_files = []
    energy_files = []
    trajectory_files = []
    restart_files = []
    coord_files = []

    for name in files:
        if name.endswith(".inp"):
            input_files.append(name)
        elif name.endswith(".log"):
            log_files.append(name)
        elif name.endswith(".ener"):
            energy_files.append(name)
        elif re.search(r"-pos-\d+\.xyz$", name):
            trajectory_files.append(name)
            coord_files.append(name)
        elif name.endswith(".restart"):
            restart_files.append(name)
        elif name.endswith(".xyz") or name.endswith(".cif"):
            coord_files.append(name)

    return {
        "input_files": sorted(input_files),
        "coord_files": sorted(set(coord_files)),
        "log_files": sorted(log_files),
        "energy_files": sorted(energy_files),
        "trajectory_files": sorted(trajectory_files),
        "restart_files": sorted(restart_files),
    }


def _available_labels(inventory: dict[str, list[str]]) -> set[str]:
    labels: set[str] = set()
    if inventory["input_files"]:
        labels.add("cp2k_input")
    if inventory["coord_files"]:
        labels.add("coordinates")
    if inventory["restart_files"]:
        labels.add("restart_file")
    if inventory["log_files"]:
        labels.add("cp2k_log")
    if inventory["energy_files"]:
        labels.add("cp2k_ener")
    if inventory["trajectory_files"]:
        labels.add("cp2k_trajectory")
    return labels


def _read_cp2k_version(executable: str) -> str | None:
    try:
        completed = subprocess.run(
            [executable, "--version"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except Exception:
        return None
    text = (completed.stdout or completed.stderr or "").strip()
    match = re.search(r"CP2K(?:\s+version)?\s+([0-9][^\s]*)", text, re.IGNORECASE)
    if match:
        return match.group(1)
    first_line = text.splitlines()[0].strip() if text else ""
    return first_line or None


def _estimate_atom_count(calc_dir: Path, inventory: dict[str, list[str]]) -> int:
    for name in inventory["coord_files"]:
        path = calc_dir / name
        if not path.is_file():
            continue
        try:
            if path.suffix.lower() == ".cif":
                _, atom_lines, _ = read_cif_to_xyz(path)
                return len(atom_lines)
            atom_lines, _, _ = read_xyz_structure(path)
            return len(atom_lines)
        except Exception:
            continue
    return 0


def _estimate_cp2k_resources(task: str, atom_count: int) -> dict[str, Any]:
    base_hours = {
        "energy": 1.0,
        "geo_opt": 4.0,
        "cell_opt": 6.0,
        "aimd_nvt": 8.0,
        "aimd_nve": 8.0,
        "aimd_npt": 10.0,
        "restart": 2.0,
        "parse": 0.1,
        "troubleshoot": 0.2,
    }[task]
    scale = max(1.0, atom_count / 50.0) if atom_count else 1.0
    hours = round(base_hours * scale, 1)
    nodes = max(1, int(hours / 6) or 1)
    ntasks = min(max(4, nodes * 16), 128)
    memory_gb = max(8, atom_count * 2) if atom_count else 8
    return {
        "estimated_walltime_hours": hours,
        "recommended_nodes": nodes,
        "recommended_ntasks": ntasks,
        "recommended_memory_gb": memory_gb,
        "estimated_atoms": atom_count,
    }


def _preferred_input_name(calc_dir: Path, input_path: str | None) -> str:
    if input_path:
        return Path(input_path).name
    candidates = sorted(calc_dir.glob("*.inp"))
    if candidates:
        return candidates[0].name
    return "<input.inp>"
