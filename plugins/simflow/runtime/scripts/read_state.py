#!/usr/bin/env python3
"""Read workflow, stage, job, artifact, or verification state."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from lib.state import read_state


def main():
    parser = argparse.ArgumentParser(description="Read SimFlow state")
    parser.add_argument("--file", default="workflow.json",
                        choices=["workflow.json", "stages.json", "artifacts.json",
                                 "verification.json", "jobs.json"],
                        help="State file to read")
    parser.add_argument("--base-dir", default=".", help="Base directory")
    args = parser.parse_args()

    data = read_state(args.base_dir, args.file)
    print(json.dumps(data, indent=2))


if __name__ == "__main__":
    main()
