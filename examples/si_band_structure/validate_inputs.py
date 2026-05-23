#!/usr/bin/env python3
"""Validate Si band structure VASP inputs before submission."""

import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
SIMFLOW_ROOT = SCRIPT_DIR.parent.parent
sys.path.insert(0, str(SIMFLOW_ROOT / "runtime"))
sys.path.insert(0, str(SIMFLOW_ROOT / "runtime" / "lib"))

from lib.parsers.vasp_parser import VASPParser


def validate_step(step: str) -> list:
    """Validate VASP inputs for a step."""
    issues = []
    step_dir = SCRIPT_DIR / step

    # Check required files
    for fname in ["INCAR", "KPOINTS", "POSCAR", "vasp.slurm"]:
        fpath = step_dir / fname
        if not fpath.exists():
            issues.append(f"{step}/{fname} missing")
        elif fpath.stat().st_size == 0:
            issues.append(f"{step}/{fname} is empty")

    # Check INCAR
    incar = step_dir / "INCAR"
    if incar.exists():
        content = incar.read_text()
        if "SYSTEM" not in content:
            issues.append(f"{step}/INCAR missing SYSTEM tag")
        if "ENCUT" not in content:
            issues.append(f"{step}/INCAR missing ENCUT")

    # Check POSCAR
    poscar = step_dir / "POSCAR"
    if poscar.exists():
        lines = poscar.read_text().strip().split("\n")
        if len(lines) < 8:
            issues.append(f"{step}/POSCAR too short ({len(lines)} lines)")

    # Check POTCAR. Real POTCAR files are licensed and are not committed.
    potcar = step_dir / "POTCAR"
    potcar_metadata = step_dir / "POTCAR.metadata.json"
    if potcar.exists():
        first_line = potcar.read_text().split("\n")[0]
        if "Si" not in first_line:
            issues.append(f"{step}/POTCAR first line: {first_line.strip()} (expected Si)")
    elif potcar_metadata.exists():
        try:
            metadata = json.loads(potcar_metadata.read_text())
        except json.JSONDecodeError as exc:
            issues.append(f"{step}/POTCAR.metadata.json invalid JSON: {exc}")
        else:
            if metadata.get("kind") != "potcar_metadata_placeholder":
                issues.append(f"{step}/POTCAR.metadata.json has unexpected kind")
            if metadata.get("element") != "Si":
                issues.append(f"{step}/POTCAR.metadata.json element is not Si")
    else:
        issues.append(f"{step}/POTCAR missing; provide licensed POTCAR locally or keep POTCAR.metadata.json")

    # Step-specific checks
    if step == "bands":
        kpoints = step_dir / "KPOINTS"
        if kpoints.exists():
            content = kpoints.read_text()
            if "Line_mode" not in content:
                issues.append(f"{step}/KPOINTS not in line mode")

    return issues


def main():
    print("Validating Si band structure VASP inputs...")
    print("=" * 50)

    all_ok = True
    for step in ["relax", "scf", "bands"]:
        issues = validate_step(step)
        if issues:
            print(f"\n  {step.upper()}: FAIL")
            for issue in issues:
                print(f"    - {issue}")
            all_ok = False
        else:
            print(f"  {step.upper()}: OK")

    print(f"\n{'='*50}")
    if all_ok:
        missing_real_potcar = [
            step for step in ["relax", "scf", "bands"] if not (SCRIPT_DIR / step / "POTCAR").exists()
        ]
        if missing_real_potcar:
            steps = ", ".join(missing_real_potcar)
            print(f"Input metadata valid. Provide licensed POTCAR locally before real submission: {steps}.")
        else:
            print("All inputs valid. Ready for submission.")
    else:
        print("Some issues found. Fix before submission.")
        sys.exit(1)


if __name__ == "__main__":
    main()
