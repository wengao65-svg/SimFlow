#!/usr/bin/env python3
"""Parse LAMMPS output files (log and dump)."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from lib.parsers.lammps_parser import LAMMPSParser


def main():
    parser = argparse.ArgumentParser(description="Parse LAMMPS output")
    parser.add_argument("file", help="LAMMPS output file (log.lammps or dump file)")
    parser.add_argument("--check-convergence", action="store_true",
                        help="Check convergence status")
    parser.add_argument("--extract-thermo", action="store_true",
                        help="Extract thermodynamic data")
    args = parser.parse_args()

    lammps = LAMMPSParser()

    try:
        if args.check_convergence:
            result = lammps.check_convergence(args.file)
            print(json.dumps(result, indent=2))
        else:
            parsed = lammps.parse(args.file)
            output = {
                "software": parsed.software,
                "job_type": parsed.job_type,
                "converged": parsed.converged,
                "total_energy": parsed.total_energy,
                "parameters": parsed.parameters,
                "warnings": parsed.warnings,
                "errors": parsed.errors,
                "metadata": parsed.metadata,
            }
            if parsed.trajectory:
                output["trajectory_steps"] = len(parsed.trajectory)
            print(json.dumps(output, indent=2))
    except Exception as e:
        print(json.dumps({"status": "error", "message": str(e)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
