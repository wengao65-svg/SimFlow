#!/usr/bin/env python3
"""Validate presence of MLP evidence roles without judging scientific quality."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from runtime.simflow_core.helper_evidence import build_helper_evidence, source_file_record
from runtime.simflow_core.script_contracts import add_helper_recording_args, maybe_record_helper_run


BASE_REQUIRED = ["dataset_manifest", "labeling_manifest", "training_run_manifest", "model_validation_report"]
PRODUCTION_REQUIRED = BASE_REQUIRED + ["smoke_md_manifest", "anomaly_report"]
APPROVAL_REQUIRED = ["approval_record"]


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate MLP evidence role presence")
    parser.add_argument("--evidence", action="append", default=[], help="role=path evidence entry")
    parser.add_argument("--production-readiness", action="store_true")
    parser.add_argument("--require-approval", action="store_true")
    parser.add_argument("--output", default=None)
    add_helper_recording_args(parser, default_stage="analysis_visualization")
    args = parser.parse_args()

    evidence = {}
    malformed = []
    for item in args.evidence:
        if "=" not in item:
            malformed.append(item)
            continue
        role, path = item.split("=", 1)
        evidence[role.strip()] = path.strip()
    required = PRODUCTION_REQUIRED if args.production_readiness else BASE_REQUIRED
    if args.require_approval:
        required = required + APPROVAL_REQUIRED
    missing_roles = [role for role in required if role not in evidence]
    missing_paths = [
        {"role": role, "path": path}
        for role, path in evidence.items()
        if path and not Path(path).expanduser().exists()
    ]
    scientific_readiness = "ready" if not missing_roles and not missing_paths and not malformed else "blocked"
    warnings = [
        {"code": "missing_evidence_role", "message": f"Missing MLP evidence role: {role}"}
        for role in missing_roles
    ] + [
        {"code": "missing_evidence_path", "message": f"Evidence path for {item['role']} does not exist: {item['path']}"}
        for item in missing_paths
    ] + [
        {"code": "malformed_evidence_entry", "message": f"Evidence entry must use role=path form: {item}"}
        for item in malformed
    ]
    result = build_helper_evidence(
        helper="validate_mlp_evidence",
        capability="production_mlp_md_readiness_review" if args.production_readiness else "mlp_evidence_presence_review",
        status="success" if scientific_readiness == "ready" else "blocked",
        stage="analysis_visualization",
        activity="production_mlp_md_readiness_review" if args.production_readiness else "mlp_evidence_presence_review",
        evidence_role="production_md_readiness_report" if args.production_readiness else "mlp_evidence_presence_report",
        source_files=[source_file_record(path, role=role) for role, path in evidence.items()],
        actual_tool_used={"software": "custom", "support_level": "tracked_only"},
        parser_status="parsed" if not missing_paths and not malformed else "partial",
        claim_limits=[
            "This validates evidence presence only.",
            "Scientific adequacy requires domain review of the referenced evidence.",
            "Approval evidence is conditional and required only when --require-approval is set.",
        ],
        warnings=warnings,
        limitations=[
            "This validates evidence presence only.",
            "Scientific adequacy requires domain review of the referenced evidence.",
        ],
        production_readiness_requested=args.production_readiness,
        scientific_readiness=scientific_readiness,
        approval_required=args.require_approval,
        required_roles=required,
        provided_roles=sorted(evidence),
        missing_roles=missing_roles,
        missing_paths=missing_paths,
        malformed_entries=malformed,
        blocked_claims=(
            ["production MLP-MD readiness"] if args.production_readiness and scientific_readiness != "ready" else []
        ),
    )
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        result["output_file"] = str(output)
    result = maybe_record_helper_run(
        args=args,
        result=result,
        script_path=Path(__file__).resolve(),
        helper_name="validate_mlp_evidence",
        software="custom",
        input_paths=list(evidence.values()),
        output_paths=[args.output] if args.output else [],
        metadata={
            "helper_result_status": result.get("status"),
            "scientific_readiness": result.get("scientific_readiness"),
            "production_readiness": args.production_readiness,
            "approval_required": args.require_approval,
        },
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
