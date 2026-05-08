#!/usr/bin/env python3
"""Build crystal structures from element/parameters using pymatgen.

Supports creating structures from:
- Lattice parameters + element positions
- Crystal structure type (FCC, BCC, diamond, etc.)
- CIF/POSCAR file import
"""

import argparse
import json
import sys
from pathlib import Path

from pymatgen.core import Structure, Lattice


STRUCTURE_TYPES = {
    "fcc": lambda a, el: Structure(Lattice.cubic(a), [el], [[0, 0, 0]]),
    "bcc": lambda a, el: Structure(Lattice.cubic(a), [el, el], [[0, 0, 0], [0.5, 0.5, 0.5]]),
    "diamond": lambda a, el: Structure(
        Lattice.cubic(a), [el, el], [[0, 0, 0], [0.25, 0.25, 0.25]]
    ),
    "rocksalt": lambda a, el1, el2: Structure(
        Lattice.cubic(a), [el1, el2], [[0, 0, 0], [0.5, 0.5, 0.5]]
    ),
    "zincblende": lambda a, el1, el2: Structure(
        Lattice.cubic(a), [el1, el2], [[0, 0, 0], [0.25, 0.25, 0.25]]
    ),
}


def build_from_type(structure_type: str, lattice_param: float, elements: list) -> Structure:
    """Build a structure from a known crystal type."""
    stype = structure_type.lower()
    if stype not in STRUCTURE_TYPES:
        raise ValueError(f"Unknown structure type: {stype}. Available: {list(STRUCTURE_TYPES.keys())}")

    builder = STRUCTURE_TYPES[stype]
    if stype in ("rocksalt", "zincblende"):
        if len(elements) < 2:
            raise ValueError(f"{stype} requires 2 elements")
        return builder(lattice_param, elements[0], elements[1])
    return builder(lattice_param, elements[0])


def build_from_file(file_path: str) -> Structure:
    """Read structure from CIF or POSCAR file."""
    return Structure.from_file(file_path)


def build_from_params(
    lattice_a: float, lattice_b: float, lattice_c: float,
    lattice_alpha: float, lattice_beta: float, lattice_gamma: float,
    elements: list, coords: list, coords_are_fractional: bool = True,
) -> Structure:
    """Build structure from explicit lattice parameters and coordinates."""
    lattice = Lattice.from_parameters(
        lattice_a, lattice_b, lattice_c,
        lattice_alpha, lattice_beta, lattice_gamma,
    )
    if coords_are_fractional:
        return Structure(lattice, elements, coords)
    else:
        return Structure(lattice, elements, coords, coords_are_cartesian=True)


def main():
    parser = argparse.ArgumentParser(description="Build crystal structures")
    sub = parser.add_subparsers(dest="command")

    # From type
    p_type = sub.add_parser("from_type", help="Build from crystal type")
    p_type.add_argument("--type", required=True, choices=list(STRUCTURE_TYPES.keys()))
    p_type.add_argument("--lattice-param", type=float, required=True, help="Lattice parameter (Angstrom)")
    p_type.add_argument("--elements", nargs="+", required=True, help="Element symbols")
    p_type.add_argument("--output", default="POSCAR", help="Output file")
    p_type.add_argument("--format", choices=["poscar", "cif"], default="poscar")

    # From file
    p_file = sub.add_parser("from_file", help="Read from CIF/POSCAR")
    p_file.add_argument("--input", required=True, help="Input file")
    p_file.add_argument("--output", default="POSCAR", help="Output file")
    p_file.add_argument("--format", choices=["poscar", "cif"], default="poscar")

    # From parameters
    p_params = sub.add_parser("from_params", help="Build from lattice parameters")
    p_params.add_argument("--a", type=float, required=True)
    p_params.add_argument("--b", type=float, required=True)
    p_params.add_argument("--c", type=float, required=True)
    p_params.add_argument("--alpha", type=float, default=90.0)
    p_params.add_argument("--beta", type=float, default=90.0)
    p_params.add_argument("--gamma", type=float, default=90.0)
    p_params.add_argument("--elements", nargs="+", required=True)
    p_params.add_argument("--coords", nargs="+", required=True,
                          help="Coordinates as 'x,y,z' strings")
    p_params.add_argument("--fractional", action="store_true", default=True)
    p_params.add_argument("--output", default="POSCAR")
    p_params.add_argument("--format", choices=["poscar", "cif"], default="poscar")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    try:
        if args.command == "from_type":
            structure = build_from_type(args.type, args.lattice_param, args.elements)
        elif args.command == "from_file":
            structure = build_from_file(args.input)
        elif args.command == "from_params":
            coords = [list(map(float, c.split(","))) for c in args.coords]
            structure = build_from_params(
                args.a, args.b, args.c, args.alpha, args.beta, args.gamma,
                args.elements, coords, args.fractional,
            )
        else:
            parser.print_help()
            sys.exit(1)

        # Write output
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if args.format == "cif" or args.output.endswith(".cif"):
            structure.to(filename=str(output_path), fmt="cif")
        else:
            structure.to(filename=str(output_path), fmt="poscar")

        # Output metadata
        info = {
            "status": "success",
            "output": str(output_path),
            "num_atoms": len(structure),
            "elements": [str(s) for s in structure.composition.elements],
            "lattice_parameters": {
                "a": round(structure.lattice.a, 4),
                "b": round(structure.lattice.b, 4),
                "c": round(structure.lattice.c, 4),
                "alpha": round(structure.lattice.alpha, 2),
                "beta": round(structure.lattice.beta, 2),
                "gamma": round(structure.lattice.gamma, 2),
            },
            "volume": round(structure.volume, 4),
        }
        print(json.dumps(info, indent=2))

    except Exception as e:
        print(json.dumps({"status": "error", "message": str(e)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
