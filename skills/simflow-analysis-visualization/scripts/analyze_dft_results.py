#!/usr/bin/env python3
"""Analyze DFT calculation results using runtime parsers.

Supports VASP and QE output files. Extracts energy, forces, convergence
status, and other key metrics.
"""

import argparse
import importlib
import json
import sys
from pathlib import Path

# Set up runtime/lib as a package so relative imports in parsers work
_simflow_root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_simflow_root))

# Import parsers as subpackage of runtime.lib
import runtime.lib.parser as parser_mod
import runtime.lib.parsers.vasp_parser as vasp_mod
import runtime.lib.parsers.qe_parser as qe_mod

VASPParser = vasp_mod.VASPParser
QEParser = qe_mod.QEParser


PARSERS = {
    "vasp": VASPParser(),
    "qe": QEParser(),
}


def analyze_results(software: str, output_files: list) -> dict:
    """Analyze one or more output files from a DFT calculation."""
    if software not in PARSERS:
        raise ValueError("Unsupported software: {}. Supported: {}".format(software, list(PARSERS.keys())))

    parser = PARSERS[software]
    results = []

    for f in output_files:
        if not Path(f).exists():
            results.append({"file": f, "status": "error", "message": "File not found"})
            continue

        try:
            parsed = parser.parse(f)
            convergence = parser.check_convergence(f)
            results.append({
                "file": f,
                "status": "success",
                "converged": parsed.converged,
                "final_energy": parsed.final_energy,
                "total_energy": parsed.total_energy,
                "job_type": parsed.job_type,
                "parameters": parsed.parameters,
                "warnings": parsed.warnings,
                "errors": parsed.errors,
                "metadata": parsed.metadata,
                "convergence": convergence,
            })
        except Exception as e:
            results.append({"file": f, "status": "error", "message": str(e)})

    successful = [r for r in results if r["status"] == "success"]
    energies = [r["final_energy"] for r in successful if r.get("final_energy") is not None]

    return {
        "software": software,
        "num_files": len(output_files),
        "num_successful": len(successful),
        "all_converged": all(r.get("converged", False) for r in successful),
        "final_energy": energies[-1] if energies else None,
        "energy_range": [min(energies), max(energies)] if energies else None,
        "results": results,
    }


def main():
    parser = argparse.ArgumentParser(description="Analyze DFT calculation results")
    parser.add_argument("--software", required=True, choices=["vasp", "qe"],
                        help="Computational software")
    parser.add_argument("--files", nargs="+", required=True,
                        help="Output files to analyze")
    args = parser.parse_args()

    try:
        result = analyze_results(args.software, args.files)
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(json.dumps({"status": "error", "message": str(e)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
