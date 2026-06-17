#!/usr/bin/env python3
"""Generate CP2K input files from CIF structure.

Reads a CIF structure file, converts to XYZ, and generates CP2K input
for AIMD NVT or DFT single-point calculations.

Usage:
    python generate_cp2k_inputs.py --cif structure.cif --job-type aimd_nvt -o cp2k-out
    python generate_cp2k_inputs.py --cif structure.cif --job-type energy -o cp2k-out \
        --params '{"coord_file": "last_frame.xyz"}'
"""

import argparse
import json
import sys
from pathlib import Path

SIMFLOW_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(SIMFLOW_ROOT))
sys.path.insert(0, str(SIMFLOW_ROOT / "runtime"))

from runtime.simflow_core.script_contracts import add_helper_recording_args, maybe_record_helper_run
from runtime.simflow_helpers.engines.cp2k_input import generate_cp2k_input_package


def generate_cp2k_inputs(
    cif_path: str,
    job_type: str,
    output_dir: str,
    params: dict | None = None,
) -> dict:
    """Generate CP2K input files.

    Args:
        cif_path: Path to CIF structure file
        job_type: "aimd_nvt" or "energy"
        output_dir: Output directory
        params: Optional parameter overrides

    Returns:
        Result dict with status, files_generated, parameters
    """
    result = generate_cp2k_input_package(cif_path, job_type, output_dir, params=params)
    result["compatibility_route"] = "simflow-computation/generate_cp2k_inputs.py"
    return result


def main():
    parser = argparse.ArgumentParser(description="Generate CP2K input files")
    parser.add_argument("--cif", required=True, help="Path to CIF structure file")
    parser.add_argument(
        "--job-type", required=True, choices=["aimd_nvt", "energy"],
        help="Calculation type",
    )
    parser.add_argument("-o", "--output-dir", required=True, help="Output directory")
    parser.add_argument("--params", default="{}", help="JSON string of parameter overrides")
    add_helper_recording_args(parser, default_stage="computation")
    args = parser.parse_args()

    try:
        params = json.loads(args.params)
        result = generate_cp2k_inputs(args.cif, args.job_type, args.output_dir, params)
        result = maybe_record_helper_run(
            args=args,
            result=result,
            script_path=Path(__file__).resolve(),
            helper_name="generate_cp2k_inputs",
            software="cp2k",
            input_paths=[args.cif],
            output_paths=result.get("files_generated", []),
        )
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(json.dumps({"status": "error", "message": str(e)}), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
