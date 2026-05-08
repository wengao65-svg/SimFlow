#!/usr/bin/env python3
"""Parse Gaussian output files (.log)."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from lib.parsers.gaussian_parser import GaussianParser


def main():
    parser = argparse.ArgumentParser(description="Parse Gaussian output")
    parser.add_argument("file", help="Gaussian output file (.log)")
    parser.add_argument("--check-convergence", action="store_true",
                        help="Check convergence status")
    parser.add_argument("--extract-frequencies", action="store_true",
                        help="Extract vibrational frequencies")
    args = parser.parse_args()

    gauss = GaussianParser()

    try:
        if args.check_convergence:
            result = gauss.check_convergence(args.file)
            print(json.dumps(result, indent=2))
        else:
            parsed = gauss.parse(args.file)
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
            if args.extract_frequencies and parsed.trajectory:
                output["frequencies"] = parsed.trajectory
            print(json.dumps(output, indent=2))
    except Exception as e:
        print(json.dumps({"status": "error", "message": str(e)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
