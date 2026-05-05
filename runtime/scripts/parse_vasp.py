#!/usr/bin/env python3
"""Parse VASP output files and extract structured results.

For a calculation directory, prefer py4vasp when vaspout.h5 exists and
py4vasp is installed. Otherwise fall back to SimFlow parsers.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from lib.parsers.vasp_parser import VASPParser
from lib.vasp_py4vasp import can_use_py4vasp, read_with_py4vasp


def main():
    parser = argparse.ArgumentParser(description="Parse VASP output")
    parser.add_argument("file", help="VASP output file or calculation directory")
    parser.add_argument("--check-convergence", action="store_true",
                        help="Check convergence status")
    parser.add_argument("--extract-energy", action="store_true",
                        help="Extract energy values")
    parser.add_argument("--extract-forces", action="store_true",
                        help="Extract force data")
    parser.add_argument("--quantity", default="summary",
                        help="py4vasp quantity for directory parsing")
    args = parser.parse_args()

    vasp = VASPParser()

    try:
        target = Path(args.file)
        if target.is_dir():
            py4 = can_use_py4vasp(str(target))
            if py4["usable"]:
                print(json.dumps(read_with_py4vasp(str(target), args.quantity), indent=2, default=str))
                return

            fallback_files = [name for name in ("vasprun.xml", "OUTCAR", "OSZICAR", "EIGENVAL") if (target / name).is_file()]
            if not fallback_files:
                print(json.dumps({
                    "status": "error",
                    "backend": "simflow_fallback",
                    "message": "No parseable VASP fallback files found",
                    "py4vasp": py4,
                }, indent=2))
                sys.exit(1)
            args.file = str(target / fallback_files[0])

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
