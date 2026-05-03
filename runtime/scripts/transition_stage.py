#!/usr/bin/env python3
"""Execute a stage state transition."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from lib.state import update_stage, read_state
from lib.gates import check_gate, record_gate_decision


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
    parser.add_argument("--gate", help="Gate name to check before transition")
    parser.add_argument("--gate-context", help="JSON string with gate condition values")
    parser.add_argument("--approve-gate", action="store_true",
                        help="Record gate approval after conditions pass")
    args = parser.parse_args()

    # Gate check: block transition if gate conditions not met
    if args.gate:
        context = {}
        if args.gate_context:
            context = json.loads(args.gate_context)
        gate_result = check_gate(args.gate, context)
        if gate_result["status"] != "pass":
            print(json.dumps({
                "status": "blocked",
                "gate": args.gate,
                "gate_result": gate_result,
            }, indent=2))
            sys.exit(1)
        if args.approve_gate:
            record_gate_decision(
                args.gate, "approved", context,
                base_dir=args.base_dir,
                agent=args.agent or "",
            )

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

    from_stage = current
    result = update_stage(args.stage, args.status, args.base_dir, **kwargs)
    output = {
        "status": "success",
        "stage": args.stage,
        "from": from_stage,
        "to": args.status,
    }
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
