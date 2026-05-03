#!/usr/bin/env python3
"""Parse VASP output files and extract structured results."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from lib.parsers.vasp_parser import VASPParser


def main():
    parser = argparse.ArgumentParser(description="Parse VASP output")
    parser.add_argument("file", help="VASP output file (OUTCAR, OSZICAR, or vasprun.xml)")
    parser.add_argument("--check-convergence", action="store_true",
                        help="Check convergence status")
    parser.add_argument("--extract-energy", action="store_true",
                        help="Extract energy values")
    parser.add_argument("--extract-forces", action="store_true",
                        help="Extract force data")
    args = parser.parse_args()

    vasp = VASPParser()

    try:
        if args.check_convergence:
            result = vasp.check_convergence(args.file)
            print(json.dumps(result, indent=2))
        else:
            parsed = vasp.parse(args.file)
            output = {
                "software": parsed.software,
                "job_type": parsed.job_type,
                "converged": parsed.converged,
                "total_energy": parsed.total_energy,
                "final_energy": parsed.final_energy,
                "parameters": parsed.parameters,
                "warnings": parsed.warnings,
                "errors": parsed.errors,
                "metadata": parsed.metadata,
            }
            if args.extract_forces and parsed.forces:
                output["forces"] = parsed.forces
            if parsed.trajectory:
                output["trajectory_steps"] = len(parsed.trajectory)
            print(json.dumps(output, indent=2))
    except Exception as e:
        print(json.dumps({"status": "error", "message": str(e)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
