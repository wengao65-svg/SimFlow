#!/usr/bin/env python3
"""Prepare GPUMD/NEP evidence handoff JSON from existing evidence files."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from runtime.simflow_core.script_contracts import add_helper_recording_args, maybe_record_helper_run
from runtime.simflow_core.toolchains import classify_tool_support, support_level_for_capability
from runtime.simflow_helpers.adapters import adapter_capabilities


def _load_json(path: str) -> dict:
    candidate = Path(path)
    if not candidate.is_file():
        return {"path": str(candidate), "present": False}
    try:
        data = json.loads(candidate.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {"path": str(candidate), "present": True, "parse_error": str(exc)}
    return {"path": str(candidate), "present": True, "data": data}


def _degraded(items: list[dict]) -> bool:
    for item in items:
        if not item.get("present"):
            return True
        if item.get("parse_error"):
            return True
        data = item.get("data")
        if isinstance(data, dict) and data.get("status") in {"warning", "blocked", "capability_warning"}:
            return True
    return False


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare GPUMD/NEP handoff evidence")
    parser.add_argument("--manifest", action="append", default=[], help="Manifest JSON path")
    parser.add_argument("--inspection", action="append", default=[], help="Inspection JSON path")
    parser.add_argument("--parsed-output", action="append", default=[], help="Parsed output JSON path")
    parser.add_argument("--output", required=True, help="Handoff JSON output")
    parser.add_argument("--summary", default="GPUMD/NEP tracked-only evidence handoff")
    parser.add_argument("--next-action", action="append", default=[])
    add_helper_recording_args(parser, default_stage="writing")
    args = parser.parse_args()

    support = classify_tool_support(["gpumd", "nep"])
    manifests = [_load_json(path) for path in args.manifest]
    inspections = [_load_json(path) for path in args.inspection]
    parsed_outputs = [_load_json(path) for path in args.parsed_output]
    degraded = _degraded(manifests) or _degraded(inspections) or _degraded(parsed_outputs)
    blocked = not (manifests or inspections or parsed_outputs)
    handoff = {
        "status": "blocked" if blocked else ("warning" if degraded else "success"),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "summary": args.summary,
        "capability": "evidence_handoff",
        "capability_support_level": support_level_for_capability("gpumd", "evidence_handoff"),
        "adapter_capabilities": adapter_capabilities("gpumd"),
        "tool_support": support,
        "manifests": manifests,
        "inspections": inspections,
        "parsed_outputs": parsed_outputs,
        "next_actions": args.next_action,
        "approval_needed": [
            "real local execution",
            "remote execution",
            "HPC submit",
            "production MLP-MD readiness",
        ],
        "limitations": [
            "GPUMD/NEP remain tracked_only tools.",
            "This handoff does not certify execution, convergence, or production readiness.",
        ],
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(handoff, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    handoff["output_file"] = str(output)
    input_paths = args.manifest + args.inspection + args.parsed_output
    handoff = maybe_record_helper_run(
        args=args,
        result=handoff,
        script_path=Path(__file__).resolve(),
        helper_name="prepare_gpumd_handoff",
        software="gpumd",
        input_paths=input_paths,
        output_paths=[str(output)],
        metadata={"capability": "evidence_handoff", "helper_result_status": handoff.get("status")},
    )
    print(json.dumps(handoff, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
