"""Tool: Scan project root for compute directories not registered in jobs.json."""

import json
import os
from pathlib import Path
from typing import Any

from runtime.simflow_core.state import ProjectRootError, read_state, resolve_project_root

# File patterns that indicate a real compute directory
COMPUTE_MARKERS = {
    "job_logs": ["train.log", "slurm-*.out", "*.nohup", "*.pid", "parallel_launcher.log", "serial_driver.nohup"],
    "vasp": ["OUTCAR", "vasprun.xml", "OSZICAR", "INCAR"],
    "cp2k": ["*.log", "project-*.inp"],
    "gpumd_nep": ["nep.in", "train.xyz", "nep.restart", "loss.out", "thermo.out"],
    "gpumd_md": ["run.in", "model.xyz", "thermo.out", "neighbor.out"],
    "lammps": ["in.*", "log.lammps", "data.*"],
    "python_scripts": ["run_*.sh", "launch_*.sh", "submit_*.sh"],
}

# Directory name patterns that suggest compute work
RISKY_DIR_PATTERNS = ["*NoGate*", "*Relaxed*", "*Bypass*", "*SkipGate*", "*Skip*Gate*"]


def _project_root(params: dict) -> str:
    project_root = params.get("project_root")
    if not project_root:
        raise ProjectRootError("project_root is required for MCP read operations")
    return project_root


def _matches_any(path: Path, patterns: list[str]) -> bool:
    for pattern in patterns:
        if path.match(pattern) or path.name == pattern:
            return True
    return False


def _scan_directory_for_markers(dir_path: Path) -> dict[str, list[str]]:
    """Scan a directory for compute marker files."""
    found = {}
    try:
        for item in dir_path.iterdir():
            if item.is_file():
                for category, patterns in COMPUTE_MARKERS.items():
                    if category not in found:
                        found[category] = []
                    if _matches_any(item, patterns):
                        found[category].append(item.name)
    except (PermissionError, OSError):
        pass
    # Remove empty categories
    return {k: v for k, v in found.items() if v}


def _is_registered_job(dir_path: Path, project_root: Path) -> bool:
    """Check if a directory path is referenced in any job record."""
    jobs = read_state(project_root=str(project_root), state_file="jobs.json")
    if not isinstance(jobs, list):
        return False
    dir_str = str(dir_path.relative_to(project_root))
    for job in jobs:
        if not isinstance(job, dict):
            continue
        # Check various path fields
        for field in ["remote_root", "path", "local_root", "artifact", "status_file", "driver_log"]:
            val = job.get(field, "")
            if isinstance(val, str) and dir_str in val:
                return True
    return False


def _is_registered_artifact(dir_path: Path, project_root: Path) -> bool:
    """Check if a directory path is referenced in any artifact."""
    artifacts = read_state(project_root=str(project_root), state_file="artifacts.json")
    if not isinstance(artifacts, list):
        return False
    dir_str = str(dir_path.relative_to(project_root))
    for art in artifacts:
        if not isinstance(art, dict):
            continue
        path = art.get("path", "")
        if isinstance(path, str) and (dir_str in path or path.startswith(dir_str)):
            return True
    return False


def execute(params: dict) -> dict:
    """Scan project_root for compute directories not registered in SimFlow state.

    Looks for directories containing compute marker files (train.log, slurm-*.out,
    OUTCAR, nep.in+train.xyz, etc.) that are not referenced in jobs.json or
    artifacts.json. Also flags directories with risky name patterns (NoGate,
    Relaxed, Bypass, SkipGate).

    Returns a report with:
    - orphan_dirs: directories with compute markers but no job/artifact registration
    - risky_dirs: directories with risky name patterns
    - summary: counts and recommendations
    """
    try:
        project_root = _project_root(params)
        root = resolve_project_root(project_root=project_root)
    except ProjectRootError as error:
        return {"status": "error", "message": str(error)}

    max_depth = int(params.get("max_depth", 3))

    orphan_dirs = []
    risky_dirs = []

    for dir_path in root.rglob("*"):
        if not dir_path.is_dir():
            continue
        # Skip .simflow, .git, __pycache__, node_modules, etc.
        if any(part.startswith(".") and part not in (".",) for part in dir_path.relative_to(root).parts):
            continue
        if any(part in ("__pycache__", "node_modules", ".git", ".simflow") for part in dir_path.parts):
            continue
        # Depth check
        depth = len(dir_path.relative_to(root).parts)
        if depth > max_depth:
            continue

        rel_path = str(dir_path.relative_to(root))

        # Check for risky directory names
        dir_name = dir_path.name
        is_risky = any(
            pattern.replace("*", "") in dir_name
            for pattern in RISKY_DIR_PATTERNS
        )

        # Scan for compute markers
        markers = _scan_directory_for_markers(dir_path)
        has_compute = len(markers) > 0

        if not has_compute and not is_risky:
            continue

        # Check if registered
        is_registered = _is_registered_job(dir_path, root) or _is_registered_artifact(dir_path, root)

        entry = {
            "path": rel_path,
            "markers": markers,
            "is_risky_name": is_risky,
            "is_registered": is_registered,
        }

        if has_compute and not is_registered:
            orphan_dirs.append(entry)
        if is_risky:
            risky_dirs.append(entry)

    # Generate report
    report = {
        "orphan_count": len(orphan_dirs),
        "risky_count": len(risky_dirs),
        "orphan_dirs": orphan_dirs,
        "risky_dirs": risky_dirs,
        "recommendations": [],
    }

    if orphan_dirs:
        report["recommendations"].append(
            f"Found {len(orphan_dirs)} compute directories not registered in jobs.json "
            f"or artifacts.json. Consider recording them via record_computation_evidence "
            f"or registering as artifacts."
        )
    if risky_dirs:
        report["recommendations"].append(
            f"Found {len(risky_dirs)} directories with risky name patterns (NoGate, "
            f"Relaxed, Bypass, SkipGate). Consider recording gate bypass decisions "
            f"via record_user_override."
        )

    # Write report to .simflow/reports/
    from runtime.simflow_core.state import ensure_simflow_dir, write_report
    ensure_simflow_dir(project_root=str(root))
    report_lines = [
        "# Orphan Compute Scan Report",
        "",
        f"- Project root: {root}",
        f"- Orphan compute directories: {len(orphan_dirs)}",
        f"- Risky-name directories: {len(risky_dirs)}",
        "",
    ]
    if orphan_dirs:
        report_lines.append("## Orphan Compute Directories")
        report_lines.append("")
        for entry in orphan_dirs:
            report_lines.append(f"- `{entry['path']}` — markers: {', '.join(k for k in entry['markers'])}")
        report_lines.append("")
    if risky_dirs:
        report_lines.append("## Risky-Name Directories")
        report_lines.append("")
        for entry in risky_dirs:
            report_lines.append(f"- `{entry['path']}` — risky name pattern detected")
        report_lines.append("")
    if report["recommendations"]:
        report_lines.append("## Recommendations")
        report_lines.append("")
        for rec in report["recommendations"]:
            report_lines.append(f"- {rec}")
    write_report("\n".join(report_lines), project_root=str(root), report_file="orphan_compute_audit.md")

    return {"status": "success", "project_root": str(root), "data": report}
