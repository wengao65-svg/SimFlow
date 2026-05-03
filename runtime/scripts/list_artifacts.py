#!/usr/bin/env python3
"""Query and filter artifacts."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from lib.artifact import list_artifacts, get_artifact


def main():
    parser = argparse.ArgumentParser(description="List artifacts")
    parser.add_argument("--stage", help="Filter by stage")
    parser.add_argument("--artifact-id", help="Get specific artifact by ID")
    parser.add_argument("--base-dir", default=".", help="Base directory")
    args = parser.parse_args()

    if args.artifact_id:
        art = get_artifact(args.artifact_id, args.base_dir)
        if art:
            print(json.dumps(art, indent=2))
        else:
            print(json.dumps({"status": "error", "message": f"Artifact not found: {args.artifact_id}"}))
            sys.exit(1)
    else:
        arts = list_artifacts(stage=args.stage, base_dir=args.base_dir)
        print(json.dumps(arts, indent=2))


if __name__ == "__main__":
    main()
