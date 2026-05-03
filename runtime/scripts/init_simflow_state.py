#!/usr/bin/env python3
"""Initialize .simflow/ directory structure and initial workflow state."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from lib.state import init_workflow, ensure_simflow_dir


def main():
    parser = argparse.ArgumentParser(description="Initialize SimFlow state")
    parser.add_argument("--workflow-type", required=True, choices=["dft", "aimd", "md", "custom"],
                        help="Workflow type")
    parser.add_argument("--entry-point", default="literature",
                        help="Entry stage name (default: literature)")
    parser.add_argument("--base-dir", default=".", help="Base directory")
    args = parser.parse_args()

    ensure_simflow_dir(args.base_dir)
    state = init_workflow(args.workflow_type, args.entry_point, args.base_dir)
    output = {
        "status": "success",
        "path": args.base_dir,
        "workflow_id": state.get("workflow_id"),
        "workflow_type": state.get("workflow_type"),
        "current_stage": state.get("current_stage"),
    }
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
