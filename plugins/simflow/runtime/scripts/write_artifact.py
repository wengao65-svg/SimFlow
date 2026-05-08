#!/usr/bin/env python3
"""Register an artifact and write its metadata."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from lib.artifact import register_artifact


def main():
    parser = argparse.ArgumentParser(description="Register artifact")
    parser.add_argument("--name", required=True, help="Artifact file name")
    parser.add_argument("--type", required=True, dest="artifact_type",
                        help="Artifact type (e.g., literature_matrix, proposal)")
    parser.add_argument("--stage", required=True, help="Producing stage")
    parser.add_argument("--path", help="Relative path to artifact file")
    parser.add_argument("--parent-artifacts", nargs="*", default=[],
                        help="Parent artifact IDs")
    parser.add_argument("--parameters", help="JSON string of parameters")
    parser.add_argument("--software", help="Software used (if applicable)")
    parser.add_argument("--base-dir", default=".", help="Base directory")
    args = parser.parse_args()

    params = None
    if args.parameters:
        try:
            params = json.loads(args.parameters)
        except json.JSONDecodeError:
            print(json.dumps({"status": "error", "message": "Invalid --parameters JSON"}))
            sys.exit(1)

    artifact = register_artifact(
        name=args.name,
        artifact_type=args.artifact_type,
        stage=args.stage,
        base_dir=args.base_dir,
        path=args.path,
        parent_artifacts=args.parent_artifacts or None,
        parameters=params,
        software=args.software,
    )
    print(json.dumps(artifact, indent=2))


if __name__ == "__main__":
    main()
