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

from runtime.simflow_core.result_contract import attach_simflow_result
from runtime.simflow_core.script_contracts import add_helper_recording_args, maybe_record_helper_run


UNSUPPORTED_PLACEHOLDER_SOFTWARE = {"qe", "quantum_espresso", "gaussian"}


def _unsupported_placeholder_check(software: str) -> dict:
    return {
        "check": "unsupported_placeholder",
        "passed": False,
        "message": (
            f"{software} verification is not supported in this SimFlow product build; "
            "record user-provided files through generic artifact or evidence intake."
        ),
        "software": software,
        "support_level": "unsupported_placeholder",
    }


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
    normalized = (software or "").lower()
    if normalized in UNSUPPORTED_PLACEHOLDER_SOFTWARE:
        return _unsupported_placeholder_check(normalized)

    out_dir = Path(output_dir)

    if normalized == "vasp":
        outcar = out_dir / "OUTCAR"
        if outcar.exists():
            content = outcar.read_text(errors="replace")
            converged = "reached required accuracy" in content
            return {
                "check": "convergence",
                "passed": converged,
                "message": "VASP convergence: {}".format("reached" if converged else "NOT reached"),
            }

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


def _verification_status(checks: list[dict]) -> tuple[str, str | None, str]:
    if not checks:
        return "pending", "no_checks_executed", "No verification checks were executed."
    if all(check.get("passed") for check in checks):
        return "pass", None, "All verification checks passed."
    return "fail", "verification_checks_failed", "One or more verification checks failed."


def _verification_outcome(verification_status: str) -> str:
    return {
        "pass": "success",
        "warning": "warning",
        "fail": "blocked",
        "pending": "waiting",
    }[verification_status]


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
            "lammps": ["log.lammps", "dump.lammps"],
        }
        if software and software in expected:
            checks.append(verify_outputs_exist(output_dir, expected[software]))

    # Summary
    passed = sum(1 for c in checks if c["passed"])
    total = len(checks)
    verification_status, reason_code, message = _verification_status(checks)

    result = {
        "status": "success",
        "stage": stage,
        "software": software,
        "verification_status": verification_status,
        "total_checks": total,
        "passed": passed,
        "failed": total - passed,
        "all_passed": total > 0 and passed == total,
        "checks": checks,
        "message": message,
    }
    if reason_code:
        result["reason_code"] = reason_code
    return attach_simflow_result(
        result,
        role="helper",
        activity="verification",
        legacy_status=result.get("status"),
        stage=stage or "analysis_visualization",
        outcome=_verification_outcome(verification_status),
        reason_code=reason_code,
        state_effect="none",
        verification_status=verification_status,
    )


def main():
    parser = argparse.ArgumentParser(description="Run workflow verification")
    parser.add_argument("--workflow-dir", required=True, help="Path to .simflow directory")
    parser.add_argument("--stage", help="Stage to verify")
    parser.add_argument("--software", choices=["vasp", "lammps", "qe", "quantum_espresso", "gaussian"],
                        help="Software type")
    parser.add_argument("--output-dir", help="Directory containing calculation outputs")
    add_helper_recording_args(parser, default_stage="analysis_visualization")
    args = parser.parse_args()

    try:
        result = run_verification(args.workflow_dir, args.stage,
                                  args.software, args.output_dir)
        result = maybe_record_helper_run(
            args=args,
            result=result,
            script_path=Path(__file__).resolve(),
            helper_name="run_verification",
            software=args.software,
            input_paths=[args.output_dir] if args.output_dir else [],
        )
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(json.dumps({"status": "error", "message": str(e)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
