"""Optional VASP tool adapters.

This module detects and plans safe VASPKIT usage. It does not replace
VASPKIT and it does not submit calculations.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any


_TASK_TO_VASPKIT_CODES = {
    "potcar_metadata": ["103"],
    "kpath": ["302"],
    "band": ["211"],
    "dos": ["111"],
    "structure_summary": ["101"],
}


def detect_vaspkit(executable: str = "vaspkit") -> dict[str, Any]:
    """Detect a local VASPKIT executable without requiring it."""
    path = shutil.which(executable)
    if not path:
        return {
            "available": False,
            "executable": executable,
            "path": None,
            "version": None,
            "message": "VASPKIT not found in PATH",
        }

    version = None
    try:
        result = subprocess.run(
            [path, "-version"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        text = (result.stdout or result.stderr).strip()
        version = text.splitlines()[0] if text else None
    except (OSError, subprocess.TimeoutExpired):
        version = None

    return {
        "available": True,
        "executable": executable,
        "path": path,
        "version": version,
        "message": "VASPKIT detected",
    }


def plan_vaspkit_task(task: str, work_dir: str, inputs: dict[str, Any] | None = None) -> dict[str, Any]:
    """Build a dry-run VASPKIT plan for common pre/post-processing tasks."""
    tool = detect_vaspkit()
    inputs = inputs or {}
    codes = _TASK_TO_VASPKIT_CODES.get(task, [])
    safe_to_execute = task in {"kpath", "band", "dos", "structure_summary"}

    return {
        "tool": "vaspkit",
        "task": task,
        "available": tool["available"],
        "tool_info": tool,
        "work_dir": str(Path(work_dir)),
        "interactive_codes": codes,
        "inputs": inputs,
        "safe_to_execute": safe_to_execute,
        "dry_run": True,
        "warnings": [] if safe_to_execute else [
            "This task is metadata-only or requires user-owned licensed data; SimFlow will not generate or distribute POTCAR content."
        ],
    }


def run_vaspkit_safe(plan: dict[str, Any], execute: bool = False, timeout: int = 60) -> dict[str, Any]:
    """Execute a planned VASPKIT task only when explicitly allowed."""
    if not execute:
        return {"status": "dry_run", "plan": plan}
    if not plan.get("safe_to_execute"):
        return {"status": "blocked", "message": "VASPKIT task is not marked safe to execute", "plan": plan}
    if not plan.get("available"):
        return {"status": "unavailable", "message": "VASPKIT not available", "plan": plan}

    codes = plan.get("interactive_codes") or []
    if not codes:
        return {"status": "blocked", "message": "No VASPKIT codes configured for task", "plan": plan}

    work_dir = Path(plan["work_dir"])
    work_dir.mkdir(parents=True, exist_ok=True)
    executable = plan["tool_info"]["path"]
    try:
        result = subprocess.run(
            [executable],
            input="\n".join(codes) + "\n",
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(work_dir),
            check=False,
        )
    except subprocess.TimeoutExpired:
        return {"status": "error", "message": "VASPKIT timed out", "plan": plan}

    return {
        "status": "success" if result.returncode == 0 else "error",
        "returncode": result.returncode,
        "stdout_tail": result.stdout[-2000:],
        "stderr_tail": result.stderr[-2000:],
        "plan": plan,
    }
