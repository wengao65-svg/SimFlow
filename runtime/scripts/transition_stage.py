#!/usr/bin/env python3
"""Execute a stage state transition."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from lib.state import update_stage, read_state


VALID_TRANSITIONS = {
    "pending": ["in_progress"],
    "in_progress": ["completed", "failed"],
    "failed": ["in_progress"],  # retry
    "completed": [],  # terminal
}


def main():
    parser = argparse.ArgumentParser(description="Transition stage state")
    parser.add_argument("--stage", required=True, help="Stage name")
    parser.add_argument("--status", required=True,
                        choices=["pending", "in_progress", "completed", "failed"],
                        help="New status")
    parser.add_argument("--agent", help="Agent name")
    parser.add_argument("--base-dir", default=".", help="Base directory")
    args = parser.parse_args()

    # Validate transition
    stages = read_state(args.base_dir, "stages.json")
    current = stages.get(args.stage, {}).get("status", "pending")
    allowed = VALID_TRANSITIONS.get(current, [])
    if args.status not in allowed:
        print(json.dumps({
            "status": "error",
            "message": f"Invalid transition: {current} -> {args.status}. Allowed: {allowed}",
        }))
        sys.exit(1)

    kwargs = {}
    if args.agent:
        kwargs["agent"] = args.agent

    result = update_stage(args.stage, args.status, args.base_dir, **kwargs)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
