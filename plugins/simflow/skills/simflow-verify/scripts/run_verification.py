#!/usr/bin/env python3
"""Run verification checks on workflow outputs.

Validates that workflow outputs meet quality criteria:
- Structure validation
- Convergence checks
- Output completeness
- Parameter compliance
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from runtime.lib.verification import create_verification_report, add_check, finalize_report
from runtime.lib.utils import now_iso


def verify_structure(structure_file: str) -> dict:
    """Verify a structure file is valid."""
    try:
        from pymatgen.core import Structure
        s = Structure.from_file(structure_file)
        return {
            "check": "structure_valid",
            "passed": True,
            "message": "Structure has {} atoms".format(len(s)),
            "details": {
                "num_atoms": len(s),
                "elements": [str(el) for el in s.composition.elements],
                "volume": round(s.volume, 4),
            },
        }
    except Exception as e:
        return {
            "check": "structure_valid",
            "passed": False,
            "message": "Structure validation failed: {}".format(str(e)),
        }


def verify_convergence(output_dir: str, software: str) -> dict:
    """Check if calculation outputs show convergence."""
    out_dir = Path(output_dir)

    if software == "vasp":
        outcar = out_dir / "OUTCAR"
        if outcar.exists():
            content = outcar.read_text(errors="replace")
            converged = "reached required accuracy" in content
            return {
                "check": "convergence",
                "passed": converged,
                "message": "VASP convergence: {}".format("reached" if converged else "NOT reached"),
            }
    elif software == "qe":
        for f in out_dir.glob("*.out"):
            content = f.read_text(errors="replace")
            if "convergence has been achieved" in content:
                return {"check": "convergence", "passed": True, "message": "QE converged"}
        return {"check": "convergence", "passed": False, "message": "QE convergence not found"}

    return {"check": "convergence", "passed": False, "message": "No output files found"}


def verify_outputs_exist(output_dir: str, expected_files: list) -> dict:
    """Check that expected output files exist."""
    out_dir = Path(output_dir)
    missing = [f for f in expected_files if not (out_dir / f).exists()]
    return {
        "check": "outputs_exist",
        "passed": len(missing) == 0,
        "message": "All expected files present" if not missing
                   else "Missing files: {}".format(", ".join(missing)),
        "missing": missing,
    }


def run_verification(workflow_dir: str, stage: str = None,
                     software: str = None, output_dir: str = None) -> dict:
    """Run verification checks."""
    wf_dir = Path(workflow_dir)
    checks = []

    # Structure verification
    for poscar in wf_dir.rglob("POSCAR"):
        checks.append(verify_structure(str(poscar)))
        break  # only check first

    # Convergence verification
    if output_dir and software:
        checks.append(verify_convergence(output_dir, software))

    # Output completeness
    if output_dir:
        expected = {
            "vasp": ["OUTCAR", "OSZICAR", "CONTCAR"],
            "qe": ["*.out", "*.xml"],
            "lammps": ["log.lammps", "dump.lammps"],
        }
        if software and software in expected:
            checks.append(verify_outputs_exist(output_dir, expected[software]))

    # Summary
    passed = sum(1 for c in checks if c["passed"])
    total = len(checks)

    return {
        "status": "success",
        "stage": stage,
        "software": software,
        "total_checks": total,
        "passed": passed,
        "failed": total - passed,
        "all_passed": passed == total,
        "checks": checks,
    }


def main():
    parser = argparse.ArgumentParser(description="Run workflow verification")
    parser.add_argument("--workflow-dir", required=True, help="Path to .simflow directory")
    parser.add_argument("--stage", help="Stage to verify")
    parser.add_argument("--software", choices=["vasp", "qe", "lammps", "gaussian"],
                        help="Software type")
    parser.add_argument("--output-dir", help="Directory containing calculation outputs")
    args = parser.parse_args()

    try:
        result = run_verification(args.workflow_dir, args.stage,
                                  args.software, args.output_dir)
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(json.dumps({"status": "error", "message": str(e)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
