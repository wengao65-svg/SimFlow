#!/usr/bin/env python3
"""Prepare a generic MLP evidence handoff package."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from runtime.simflow_core.script_contracts import add_helper_recording_args, maybe_record_helper_run


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare MLP evidence handoff JSON")
    parser.add_argument("--evidence", action="append", default=[], help="role=path evidence entry")
    parser.add_argument("--output", required=True)
    parser.add_argument("--goal", default=None)
    parser.add_argument("--toolchain", default=None)
    parser.add_argument("--iteration-id", default=None)
    parser.add_argument("--risk", action="append", default=[])
    parser.add_argument("--next-action", action="append", default=[])
    add_helper_recording_args(parser, default_stage="writing")
    args = parser.parse_args()

    evidence = []
    for item in args.evidence:
        if "=" not in item:
            evidence.append({"role": None, "path": item, "present": Path(item).expanduser().exists(), "warning": "missing role"})
            continue
        role, path = item.split("=", 1)
        evidence.append({"role": role.strip(), "path": path.strip(), "present": Path(path.strip()).expanduser().exists()})
    degraded = any((not item.get("present")) or item.get("warning") for item in evidence)
    handoff = {
        "status": "blocked" if not evidence else ("warning" if degraded else "success"),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "recipe": "mlp_md",
        "goal": args.goal,
        "iteration_id": args.iteration_id,
        "toolchain": [item.strip() for item in args.toolchain.split(",")] if args.toolchain else [],
        "evidence": evidence,
        "risks": args.risk,
        "next_actions": args.next_action,
        "approval_needed_for": [
            "real local training or MD",
            "remote execution",
            "HPC submit",
            "production MLP-MD readiness",
        ],
        "limitations": [
            "This handoff records evidence presence and provenance.",
            "It does not execute training or certify model quality.",
        ],
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(handoff, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    handoff["output_file"] = str(output)
    input_paths = [item["path"] for item in evidence if item.get("path")]
    handoff = maybe_record_helper_run(
        args=args,
        result=handoff,
        script_path=Path(__file__).resolve(),
        helper_name="prepare_mlp_handoff",
        software="custom",
        input_paths=input_paths,
        output_paths=[str(output)],
        metadata={"evidence_role": "mlp_handoff", "helper_result_status": handoff.get("status")},
    )
    print(json.dumps(handoff, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
