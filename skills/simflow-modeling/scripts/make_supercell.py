#!/usr/bin/env python3
"""Generate supercells from a structure file using pymatgen."""

import argparse
import json
import sys
from pathlib import Path

from pymatgen.core import Structure


def make_supercell(input_file: str, scale_matrix: list, output_file: str, fmt: str = "poscar") -> dict:
    """Create a supercell from a structure file.

    Args:
        input_file: Path to POSCAR or CIF file
        scale_matrix: [nx, ny, nz] supercell dimensions
        output_file: Output file path
        fmt: Output format (poscar or cif)
    """
    structure = Structure.from_file(input_file)
    original_atoms = len(structure)

    supercell = structure.make_supercell(scale_matrix)
    supercell_atoms = len(supercell)

    # Write output
    out_path = Path(output_file)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if fmt == "cif" or output_file.endswith(".cif"):
        supercell.to(filename=str(out_path), fmt="cif")
    else:
        supercell.to(filename=str(out_path), fmt="poscar")

    return {
        "status": "success",
        "input": input_file,
        "output": str(out_path),
        "scale_matrix": scale_matrix,
        "original_atoms": original_atoms,
        "supercell_atoms": supercell_atoms,
        "lattice_parameters": {
            "a": round(supercell.lattice.a, 4),
            "b": round(supercell.lattice.b, 4),
            "c": round(supercell.lattice.c, 4),
        },
    }


def main():
    parser = argparse.ArgumentParser(description="Generate supercells")
    parser.add_argument("--input", required=True, help="Input structure file (POSCAR/CIF)")
    parser.add_argument("--nx", type=int, required=True, help="Supercell dimension along a")
    parser.add_argument("--ny", type=int, required=True, help="Supercell dimension along b")
    parser.add_argument("--nz", type=int, required=True, help="Supercell dimension along c")
    parser.add_argument("--output", default="POSCAR_supercell", help="Output file")
    parser.add_argument("--format", choices=["poscar", "cif"], default="poscar")
    args = parser.parse_args()

    try:
        result = make_supercell(args.input, [args.nx, args.ny, args.nz], args.output, args.format)
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(json.dumps({"status": "error", "message": str(e)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
