#!/usr/bin/env python3
"""Validate crystal/molecular structure for physical reasonableness."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def validate_poscar(poscar_path: str) -> dict:
    """Validate a VASP POSCAR file."""
    errors = []
    warnings = []

    try:
        content = Path(poscar_path).read_text(encoding="utf-8")
    except FileNotFoundError:
        return {"status": "fail", "errors": [f"File not found: {poscar_path}"], "warnings": []}

    lines = content.strip().split("\n")
    if len(lines) < 8:
        errors.append("POSCAR too short (< 8 lines)")
        return {"status": "fail", "errors": errors, "warnings": warnings}

    # Parse scale factor
    try:
        scale = float(lines[1].strip())
        if scale <= 0:
            errors.append(f"Invalid scale factor: {scale}")
    except ValueError:
        errors.append("Cannot parse scale factor")

    # Parse lattice vectors
    for i in range(3):
        try:
            vec = [float(x) for x in lines[2 + i].split()]
            if len(vec) != 3:
                errors.append(f"Lattice vector {i+1} does not have 3 components")
        except ValueError:
            errors.append(f"Cannot parse lattice vector {i+1}")

    # Parse atom counts
    try:
        atom_types = lines[5].split()
        atom_counts = [int(x) for x in lines[6].split()]
        if len(atom_types) != len(atom_counts):
            errors.append("Element types and counts length mismatch")
        if any(c <= 0 for c in atom_counts):
            errors.append("Atom count must be positive")
        total_atoms = sum(atom_counts)
    except (ValueError, IndexError):
        errors.append("Cannot parse atom types/counts")
        total_atoms = 0

    # Check coordinate type
    coord_line = lines[7].strip().upper()
    if coord_line[0] not in ("D", "C"):
        errors.append(f"Unknown coordinate type: {coord_line[0]}")

    # Check atom positions count
    if total_atoms > 0:
        pos_start = 8
        if coord_line[0] == "S":
            pos_start = 9
        actual_positions = len(lines) - pos_start
        if actual_positions < total_atoms:
            errors.append(f"Expected {total_atoms} positions, found {actual_positions}")

    status = "pass" if not errors else "fail"
    return {"status": status, "errors": errors, "warnings": warnings, "total_atoms": total_atoms}


def validate_cif(cif_path: str) -> dict:
    """Validate a CIF file for basic structure."""
    errors = []
    warnings = []

    try:
        content = Path(cif_path).read_text(encoding="utf-8")
    except FileNotFoundError:
        return {"status": "fail", "errors": [f"File not found: {cif_path}"], "warnings": []}

    required_fields = ["_cell_length_a", "_cell_length_b", "_cell_length_c",
                       "_cell_angle_alpha", "_cell_angle_beta", "_cell_angle_gamma"]
    for field in required_fields:
        if field not in content:
            errors.append(f"Missing required field: {field}")

    if "_atom_site_label" not in content:
        errors.append("Missing _atom_site_label (no atom data)")

    status = "pass" if not errors else "fail"
    return {"status": status, "errors": errors, "warnings": warnings}


def main():
    parser = argparse.ArgumentParser(description="Validate structure files")
    parser.add_argument("file", help="Structure file (POSCAR or CIF)")
    parser.add_argument("--format", choices=["poscar", "cif", "auto"], default="auto",
                        help="File format (default: auto-detect)")
    args = parser.parse_args()

    fmt = args.format
    if fmt == "auto":
        name = Path(args.file).name.lower()
        if "poscar" in name or name == "contcar":
            fmt = "poscar"
        elif name.endswith(".cif"):
            fmt = "cif"
        else:
            # Try POSCAR first
            fmt = "poscar"

    if fmt == "poscar":
        result = validate_poscar(args.file)
    elif fmt == "cif":
        result = validate_cif(args.file)
    else:
        result = {"status": "fail", "errors": [f"Unknown format: {fmt}"], "warnings": []}

    result["file"] = args.file
    result["format"] = fmt
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
