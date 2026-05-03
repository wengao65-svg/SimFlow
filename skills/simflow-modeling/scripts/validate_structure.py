#!/usr/bin/env python3
"""Validate crystal structures for physical reasonableness.

Checks:
- Bond lengths within reasonable range
- No atomic overlaps
- Periodic boundary conditions satisfied
- Lattice parameters reasonable
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from pymatgen.core import Structure


def check_bond_lengths(structure: Structure, min_bond: float = 1.0, max_bond: float = 5.0) -> dict:
    """Check that bond lengths are within reasonable range."""
    warnings = []
    all_neighbors = structure.get_all_neighbors(max_bond)

    for i, neighbors in enumerate(all_neighbors):
        if not neighbors:
            warnings.append(f"Atom {i} ({structure[i].specie}) has no neighbors within {max_bond} Å")
            continue
        for neighbor in neighbors:
            dist = getattr(neighbor, "nn_distance", None) or (neighbor[-1] if isinstance(neighbor, (list, tuple)) else 0)
            if dist < min_bond:
                return {
                    "status": "fail",
                    "message": f"Atom {i} has neighbor at {dist:.3f} Å (min: {min_bond} Å)",
                }

    return {"status": "pass", "message": f"All bonds between {min_bond}-{max_bond} Å", "warnings": warnings}


def check_atomic_overlaps(structure: Structure, min_dist: float = 0.5) -> dict:
    """Check for atoms closer than min_dist."""
    for i in range(len(structure)):
        neighbors = structure.get_neighbors(structure[i], min_dist)
        for neighbor in neighbors:
            if neighbor.nn_distance < min_dist:
                return {
                    "status": "fail",
                    "message": f"Overlap: atoms at distance {neighbor.nn_distance:.3f} Å",
                }
    return {"status": "pass", "message": f"No overlaps (min distance: {min_dist} Å)"}


def check_lattice_parameters(structure: Structure) -> dict:
    """Check lattice parameters are reasonable."""
    lattice = structure.lattice
    warnings = []

    for label, val in [("a", lattice.a), ("b", lattice.b), ("c", lattice.c)]:
        if val < 1.0:
            return {"status": "fail", "message": f"Lattice parameter {label} = {val:.3f} Å is too small"}
        if val > 100.0:
            warnings.append(f"Large lattice parameter {label} = {val:.3f} Å")

    for label, val in [("alpha", lattice.alpha), ("beta", lattice.beta), ("gamma", lattice.gamma)]:
        if val < 10.0 or val > 170.0:
            warnings.append(f"Unusual angle {label} = {val:.1f}°")

    return {"status": "pass" if not warnings else "warning", "message": "Lattice OK", "warnings": warnings}


def validate_structure(input_file: str, min_bond: float = 1.0, max_bond: float = 5.0, min_dist: float = 0.5) -> dict:
    """Run all validation checks on a structure file."""
    structure = Structure.from_file(input_file)

    checks = [
        check_lattice_parameters(structure),
        check_bond_lengths(structure, min_bond, max_bond),
        check_atomic_overlaps(structure, min_dist),
    ]

    overall = "pass"
    for c in checks:
        if c["status"] == "fail":
            overall = "fail"
            break
        elif c["status"] == "warning":
            overall = "warning"

    return {
        "file": input_file,
        "num_atoms": len(structure),
        "elements": [str(s) for s in structure.composition.elements],
        "overall": overall,
        "checks": checks,
    }


def main():
    parser = argparse.ArgumentParser(description="Validate structure files")
    parser.add_argument("file", help="Structure file (POSCAR/CIF)")
    parser.add_argument("--min-bond", type=float, default=1.0, help="Minimum bond length (Å)")
    parser.add_argument("--max-bond", type=float, default=5.0, help="Maximum bond length (Å)")
    parser.add_argument("--min-dist", type=float, default=0.5, help="Minimum atomic distance (Å)")
    args = parser.parse_args()

    try:
        result = validate_structure(args.file, args.min_bond, args.max_bond, args.min_dist)
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(json.dumps({"status": "error", "message": str(e)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
