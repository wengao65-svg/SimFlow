"""Declarative step-to-step file handoff for workflow pipelines.

Replaces inline shutil.copy2 calls with a declarative rule set.
Each rule specifies a source file (relative to the workflow root)
and a destination file.

Usage:
    rules = [
        {"source": "relax/output/CONTCAR", "dest": "scf/POSCAR"},
        {"source": "relax/output/CONTCAR", "dest": "bands/POSCAR"},
        {"source": "scf/output/WAVECAR", "dest": "bands/WAVECAR"},
        {"source": "scf/output/CHGCAR", "dest": "bands/CHGCAR"},
    ]
    result = resolve_handoff_rules(rules, base_dir="/path/to/workflow")
"""

import shutil
from pathlib import Path


def validate_handoff_inputs(rules: list[dict], base_dir: str = ".") -> dict:
    """Check that all source files exist before copying.

    Args:
        rules: List of {"source": ..., "dest": ...} dicts
        base_dir: Base directory for resolving relative paths

    Returns:
        {"valid": bool, "missing": [...], "errors": [...]}
    """
    base = Path(base_dir)
    missing = []
    errors = []

    for i, rule in enumerate(rules):
        source = rule.get("source")
        dest = rule.get("dest")
        if not source or not dest:
            errors.append(f"Rule {i}: missing 'source' or 'dest'")
            continue

        src_path = base / source
        if not src_path.exists():
            missing.append(str(src_path))

    return {
        "valid": len(missing) == 0 and len(errors) == 0,
        "missing": missing,
        "errors": errors,
    }


def resolve_handoff_rules(rules: list[dict], base_dir: str = ".") -> dict:
    """Execute file handoff rules: copy source files to destinations.

    Args:
        rules: List of {"source": ..., "dest": ...} dicts
        base_dir: Base directory for resolving relative paths

    Returns:
        {"copied": [...], "errors": [...]}
    """
    base = Path(base_dir)
    copied = []
    errors = []

    for i, rule in enumerate(rules):
        source = rule.get("source")
        dest = rule.get("dest")
        if not source or not dest:
            errors.append(f"Rule {i}: missing 'source' or 'dest'")
            continue

        src_path = base / source
        dst_path = base / dest

        if not src_path.exists():
            errors.append(f"Rule {i}: source not found: {src_path}")
            continue

        try:
            dst_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(src_path), str(dst_path))
            copied.append({"source": str(src_path), "dest": str(dst_path)})
        except Exception as e:
            errors.append(f"Rule {i}: copy failed ({source} -> {dest}): {e}")

    return {"copied": copied, "errors": errors}
