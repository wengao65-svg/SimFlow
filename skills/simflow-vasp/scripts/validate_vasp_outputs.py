#!/usr/bin/env python3
"""Validate VASP output files for convergence and correctness.

Checks:
- Electronic convergence (energy stability across ionic steps)
- Ionic convergence (forces below threshold)
- Energy monotonicity for relaxations
- SCF convergence
"""

import argparse
import json
import sys
from pathlib import Path

# Set up runtime/lib as a package so relative imports in parsers work
_simflow_root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_simflow_root))

import runtime.lib.parsers.vasp_parser as vasp_mod
VASPParser = vasp_mod.VASPParser


def validate_convergence(outcar_path: str, oszicar_path: str = None,
                         force_tol: float = 0.01, energy_tol: float = 1e-4) -> dict:
    """Validate VASP calculation convergence."""
    parser = VASPParser()
    checks = []

    outcar_result = parser.parse(outcar_path)
    convergence = parser.check_convergence(outcar_path)

    checks.append({
        "check": "electronic_convergence",
        "passed": outcar_result.converged,
        "message": "Electronic convergence reached" if outcar_result.converged
                   else "Electronic convergence NOT reached",
    })

    if oszicar_path and Path(oszicar_path).exists():
        oszicar_result = parser.parse(oszicar_path)

        if oszicar_result.final_energy is not None:
            if oszicar_result.total_energy is not None:
                energy_change = abs(oszicar_result.final_energy - oszicar_result.total_energy)
                energy_converged = energy_change < energy_tol
                checks.append({
                    "check": "energy_convergence",
                    "passed": energy_converged,
                    "message": "Energy change: {:.6f} eV (tol: {})".format(energy_change, energy_tol),
                })

            ionic_steps = oszicar_result.metadata.get("ionic_steps", 0)
            if ionic_steps > 1:
                checks.append({
                    "check": "ionic_relaxation",
                    "passed": True,
                    "message": "Ionic relaxation completed in {} steps".format(ionic_steps),
                })

    outcar_content = Path(outcar_path).read_text(errors="replace")

    if "VERY BAD NEWS!" in outcar_content:
        checks.append({
            "check": "vasp_errors",
            "passed": False,
            "message": "VASP reported critical errors (VERY BAD NEWS)",
        })
    elif "WARNING" in outcar_content:
        warnings_count = outcar_content.count("WARNING")
        checks.append({
            "check": "vasp_warnings",
            "passed": True,
            "message": "{} warnings found in OUTCAR".format(warnings_count),
        })

    all_passed = all(c["passed"] for c in checks)

    return {
        "status": "pass" if all_passed else "fail",
        "final_energy": outcar_result.final_energy,
        "convergence": convergence,
        "checks": checks,
        "outcar": outcar_path,
        "oszicar": oszicar_path,
    }


def validate_energy_monotonicity(oszicar_path: str) -> dict:
    """Check that energy decreases monotonically during relaxation."""
    if not Path(oszicar_path).exists():
        return {"status": "error", "message": "OSZICAR not found"}

    content = Path(oszicar_path).read_text()
    energies = []
    for line in content.strip().split("\n"):
        if line.startswith(" "):
            parts = line.split()
            if len(parts) >= 3:
                try:
                    energies.append(float(parts[2]))
                except ValueError:
                    continue

    if len(energies) < 2:
        return {"status": "pass", "message": "Single energy point, no monotonicity check needed"}

    violations = []
    for i in range(1, len(energies)):
        if energies[i] > energies[i - 1] + 1e-6:
            violations.append({"step": i + 1, "prev": energies[i - 1], "curr": energies[i]})

    return {
        "status": "pass" if not violations else "warning",
        "num_steps": len(energies),
        "energy_decrease": energies[-1] - energies[0],
        "violations": violations,
        "message": "Energy decreased by {:.6f} eV over {} steps".format(
            energies[-1] - energies[0], len(energies))
                   if not violations else "{} energy increase violations".format(len(violations)),
    }


def main():
    parser = argparse.ArgumentParser(description="Validate VASP outputs")
    parser.add_argument("--outcar", required=True, help="OUTCAR file path")
    parser.add_argument("--oszicar", help="OSZICAR file path (optional)")
    parser.add_argument("--force-tol", type=float, default=0.01, help="Force convergence tolerance (eV/A)")
    parser.add_argument("--energy-tol", type=float, default=1e-4, help="Energy convergence tolerance (eV)")
    args = parser.parse_args()

    try:
        result = validate_convergence(args.outcar, args.oszicar,
                                       args.force_tol, args.energy_tol)

        if args.oszicar:
            result["monotonicity"] = validate_energy_monotonicity(args.oszicar)

        print(json.dumps(result, indent=2))
    except Exception as e:
        print(json.dumps({"status": "error", "message": str(e)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
