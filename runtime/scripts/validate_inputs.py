#!/usr/bin/env python3
"""Validate stage inputs against stage configuration."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.validator import load_stage_config, check_required_inputs


def main():
    if len(sys.argv) < 3:
        print("Usage: validate_inputs.py <stage_name> <inputs.json>")
        sys.exit(1)

    stage_name = sys.argv[1]
    inputs_file = sys.argv[2]

    with open(inputs_file, "r") as f:
        available = json.load(f)

    stage_config = load_stage_config(stage_name)
    result = check_required_inputs(stage_config, available)

    print(json.dumps(result, indent=2))
    sys.exit(0 if result["status"] == "pass" else 1)


if __name__ == "__main__":
    main()
