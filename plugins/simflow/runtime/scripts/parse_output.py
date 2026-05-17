#!/usr/bin/env python3
"""Parse computational chemistry output files."""

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
    if len(sys.argv) < 3:
        print("Usage: parse_output.py <software> <output_file>")
        sys.exit(1)

    software = sys.argv[1].lower()
    output_file = sys.argv[2]

    if software not in PARSERS:
        print(f"Unsupported software: {software}. Supported: {list(PARSERS.keys())}")
        sys.exit(1)

    parser = PARSERS[software]()
    result = parser.parse(output_file)

    # Convert to dict for JSON serialization
    from dataclasses import asdict
    print(json.dumps(asdict(result), indent=2, default=str))


if __name__ == "__main__":
    main()
