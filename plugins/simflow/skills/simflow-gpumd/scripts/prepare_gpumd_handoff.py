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

from runtime.simflow_core.helper_evidence import build_helper_evidence, source_file_record
from runtime.simflow_core.script_contracts import add_helper_recording_args, maybe_record_helper_run
from runtime.simflow_core.toolchains import build_actual_tool_used, classify_tool_support, support_level_for_capability
from runtime.simflow_helpers.adapters import adapter_capabilities


DEGRADED_SOURCE_STATUSES = {
    "warning",
    "blocked",
    "incomplete",
    "skipped_optional_dependency",
    "capability_warning",
}
DEGRADED_PARSER_STATUSES = {"partial", "unrecognized", "missing", "malformed"}


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
        if isinstance(data, dict):
            status = str(data.get("status") or "").strip().lower()
            parser_status = str(data.get("parser_status") or "").strip().lower()
            if status in DEGRADED_SOURCE_STATUSES or parser_status in DEGRADED_PARSER_STATUSES:
                return True
    return False


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare GPUMD/NEP handoff evidence")
    parser.add_argument("--manifest", action="append", default=[], help="Manifest JSON path")
    parser.add_argument("--inspection", action="append", default=[], help="Inspection JSON path")
    parser.add_argument("--parsed-output", action="append", default=[], help="Parsed output JSON path")
    parser.add_argument("--output", required=True, help="Handoff JSON output")
    parser.add_argument("--summary", default="GPUMD/NEP helper evidence handoff")
    parser.add_argument("--next-action", action="append", default=[])
    add_helper_recording_args(parser, default_stage="writing")
    args = parser.parse_args()

    support = classify_tool_support(["gpumd", "nep"])
    manifests = [_load_json(path) for path in args.manifest]
    inspections = [_load_json(path) for path in args.inspection]
    parsed_outputs = [_load_json(path) for path in args.parsed_output]
    degraded = _degraded(manifests) or _degraded(inspections) or _degraded(parsed_outputs)
    blocked = not (manifests or inspections or parsed_outputs)
    input_paths = args.manifest + args.inspection + args.parsed_output
    source_roles = (
        [(path, "manifest") for path in args.manifest]
        + [(path, "inspection") for path in args.inspection]
        + [(path, "parsed_output") for path in args.parsed_output]
    )
    warnings = []
    for item in manifests + inspections + parsed_outputs:
        if not item.get("present"):
            warnings.append({"code": "missing_evidence_file", "message": f"Evidence file is missing: {item['path']}"})
        elif item.get("parse_error"):
            warnings.append({"code": "invalid_evidence_json", "message": f"Could not parse evidence JSON: {item['path']}"})
        else:
            data = item.get("data")
            if isinstance(data, dict):
                status = str(data.get("status") or "").strip().lower()
                parser_status = str(data.get("parser_status") or "").strip().lower()
                if status in DEGRADED_SOURCE_STATUSES:
                    warnings.append({
                        "code": "degraded_source_status",
                        "message": f"Evidence file reports status={status}: {item['path']}",
                    })
                if parser_status in DEGRADED_PARSER_STATUSES:
                    warnings.append({
                        "code": "degraded_parser_status",
                        "message": f"Evidence file reports parser_status={parser_status}: {item['path']}",
                    })
    handoff = build_helper_evidence(
        helper="prepare_gpumd_handoff",
        capability="evidence_handoff",
        status="blocked" if blocked else ("warning" if degraded else "success"),
        stage="writing",
        activity="gpumd_nep_evidence_handoff",
        evidence_role="gpumd_nep_handoff",
        source_files=[source_file_record(path, role=role) for path, role in source_roles],
        actual_tool_used=build_actual_tool_used(
            {"software": "gpumd", "helper_support": support},
            "gpumd",
        ),
        parser_status="missing" if blocked else ("partial" if degraded else "parsed"),
        claim_limits=[
            "This handoff records GPUMD/NEP helper evidence and provenance only.",
            "It does not certify execution, convergence, scientific properties, or production readiness.",
        ],
        warnings=warnings,
        limitations=[
            "GPUMD/NEP helper support does not include real execution or submit.",
            "Production MLP-MD readiness remains a simflow-mlp evidence decision.",
        ],
        created_at=datetime.now(timezone.utc).isoformat(),
        summary=args.summary,
        capability_support_level=support_level_for_capability("gpumd", "evidence_handoff"),
        adapter_capabilities=adapter_capabilities("gpumd"),
        tool_support=support,
        manifests=manifests,
        inspections=inspections,
        parsed_outputs=parsed_outputs,
        next_actions=args.next_action,
        approval_needed=[
            "real local execution",
            "remote execution",
            "HPC submit",
            "production MLP-MD readiness",
        ],
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(handoff, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    handoff["output_file"] = str(output)
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
