"""Validation utilities for stages and artifacts."""

import json
from pathlib import Path
from typing import Any


def load_stage_config(stage_name: str, workflow_dir: str = "workflow") -> dict:
    """Load a stage configuration."""
    path = Path(workflow_dir) / "stages" / f"{stage_name}.json"
    if not path.exists():
        raise FileNotFoundError(f"Stage config not found: {stage_name}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def check_required_inputs(stage_config: dict, available_inputs: list) -> dict:
    """Check if all required inputs are available."""
    required = stage_config.get("required_inputs", [])
    missing = [r for r in required if r not in available_inputs]
    return {
        "validator": "required_inputs",
        "status": "pass" if not missing else "fail",
        "message": "All required inputs available" if not missing else f"Missing inputs: {missing}",
        "details": {"required": required, "available": available_inputs, "missing": missing},
    }


def check_expected_outputs(stage_config: dict, produced_outputs: list) -> dict:
    """Check if all expected outputs were produced."""
    expected = stage_config.get("expected_outputs", [])
    missing = [e for e in expected if e not in produced_outputs]
    return {
        "validator": "expected_outputs",
        "status": "pass" if not missing else "fail",
        "message": "All expected outputs produced" if not missing else f"Missing outputs: {missing}",
        "details": {"expected": expected, "produced": produced_outputs, "missing": missing},
    }


def validate_stage(stage_name: str, available_inputs: list, produced_outputs: list, workflow_dir: str = "workflow") -> dict:
    """Run all validators for a stage."""
    stage_config = load_stage_config(stage_name, workflow_dir)
    results = [
        check_required_inputs(stage_config, available_inputs),
        check_expected_outputs(stage_config, produced_outputs),
    ]
    overall = "pass"
    for r in results:
        if r["status"] == "fail":
            overall = "fail"
            break
        elif r["status"] == "warning":
            overall = "warning"
    return {
        "stage": stage_name,
        "timestamp": __import__("datetime").datetime.now().isoformat(),
        "results": results,
        "overall": overall,
    }
