#!/usr/bin/env python3
"""Create a workflow checkpoint."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from lib.checkpoint import create_checkpoint


def main():
    parser = argparse.ArgumentParser(description="Create checkpoint")
    parser.add_argument("--workflow-id", required=True, help="Workflow ID")
    parser.add_argument("--stage", required=True, help="Stage name")
    parser.add_argument("--description", required=True, help="Checkpoint description")
    parser.add_argument("--status", default="success", help="Status (default: success)")
    parser.add_argument("--job-id", help="Optional job ID")
    parser.add_argument("--base-dir", default=".", help="Base directory")
    args = parser.parse_args()

    ckpt = create_checkpoint(
        workflow_id=args.workflow_id,
        stage_id=args.stage,
        description=args.description,
        base_dir=args.base_dir,
        status=args.status,
        job_id=args.job_id,
    )
    print(json.dumps(ckpt, indent=2))


if __name__ == "__main__":
    main()
