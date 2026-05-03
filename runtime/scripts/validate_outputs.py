#!/usr/bin/env python3
"""Validate computation output completeness and convergence."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from lib.parsers.vasp_parser import VASPParser
from lib.parsers.qe_parser import QEParser
from lib.parsers.lammps_parser import LAMMPSParser
from lib.parsers.gaussian_parser import GaussianParser


PARSERS = {
    "vasp": VASPParser,
    "qe": QEParser,
    "lammps": LAMMPSParser,
    "gaussian": GaussianParser,
}


def main():
    parser = argparse.ArgumentParser(description="Validate computation outputs")
    parser.add_argument("--software", required=True,
                        choices=["vasp", "qe", "lammps", "gaussian"],
                        help="Computational software")
    parser.add_argument("--output-file", required=True, help="Output file to validate")
    parser.add_argument("--check-energy", action="store_true", help="Check energy convergence")
    parser.add_argument("--check-forces", action="store_true", help="Check force convergence")
    args = parser.parse_args()

    parser_cls = PARSERS[args.software]
    p = parser_cls()

    try:
        convergence = p.check_convergence(args.output_file)
        result = {
            "software": args.software,
            "file": args.output_file,
            "convergence": convergence,
        }

        if args.check_energy or args.check_forces:
            parsed = p.parse(args.output_file)
            if args.check_energy:
                result["energy"] = {
                    "total_energy": parsed.total_energy,
                    "final_energy": parsed.final_energy,
                }
            if args.check_forces:
                result["forces"] = parsed.forces

        status = "pass" if convergence.get("converged", False) else "fail"
        result["status"] = status
        print(json.dumps(result, indent=2))

    except FileNotFoundError as e:
        print(json.dumps({"status": "fail", "error": str(e)}))
        sys.exit(1)
    except Exception as e:
        print(json.dumps({"status": "fail", "error": str(e)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
