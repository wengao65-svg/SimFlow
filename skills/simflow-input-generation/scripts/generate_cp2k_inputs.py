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
sys.path.insert(0, str(SIMFLOW_ROOT / "runtime"))

from lib.cp2k_input import (
    cp2k_defaults,
    generate_input,
    read_cif_to_xyz,
    write_xyz,
)


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
    params = params or {}
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    # Read CIF → XYZ + cell
    cell_abc, xyz_lines, element_counts = read_cif_to_xyz(cif_path)
    natoms = len(xyz_lines)

    # Parse cell_abc into a, b, c
    parts = cell_abc.split()
    cell_a, cell_b, cell_c = parts[0], parts[1], parts[2]

    # Write structure XYZ
    xyz_content = write_xyz(natoms, f"Generated from {Path(cif_path).name}", xyz_lines)
    xyz_path = out / "structure.xyz"
    xyz_path.write_text(xyz_content)

    # Build parameters
    calc_params = {
        "cell_a": cell_a,
        "cell_b": cell_b,
        "cell_c": cell_c,
    }
    if job_type == "aimd_nvt":
        calc_params["coord_file"] = "structure.xyz"
    elif job_type == "energy":
        calc_params["coord_file"] = params.get("coord_file", "last_frame.xyz")

    calc_params.update(params)

    # Generate input
    inp_content = generate_input(calc_params, job_type)
    inp_filename = f"{job_type}.inp"
    inp_path = out / inp_filename
    inp_path.write_text(inp_content)

    files_generated = [str(inp_path), str(xyz_path)]

    return {
        "status": "success",
        "files_generated": files_generated,
        "parameters": {
            "job_type": job_type,
            "natoms": natoms,
            "elements": element_counts,
            "cell_abc": cell_abc,
        },
    }


def main():
    parser = argparse.ArgumentParser(description="Generate CP2K input files")
    parser.add_argument("--cif", required=True, help="Path to CIF structure file")
    parser.add_argument(
        "--job-type", required=True, choices=["aimd_nvt", "energy"],
        help="Calculation type",
    )
    parser.add_argument("-o", "--output-dir", required=True, help="Output directory")
    parser.add_argument("--params", default="{}", help="JSON string of parameter overrides")
    args = parser.parse_args()

    try:
        params = json.loads(args.params)
        result = generate_cp2k_inputs(args.cif, args.job_type, args.output_dir, params)
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(json.dumps({"status": "error", "message": str(e)}), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
