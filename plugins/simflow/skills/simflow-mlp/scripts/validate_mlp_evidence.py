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
    scientific_required = PRODUCTION_REQUIRED if args.production_readiness else BASE_REQUIRED
    execution_required = APPROVAL_REQUIRED if args.require_approval else []
    required = scientific_required + execution_required
    missing_scientific_roles = [role for role in scientific_required if role not in evidence]
    missing_execution_roles = [role for role in execution_required if role not in evidence]
    missing_paths = [
        {"role": role, "path": path}
        for role, path in evidence.items()
        if path and not Path(path).expanduser().exists()
    ]
    missing_scientific_paths = [
        item for item in missing_paths
        if item["role"] in scientific_required
    ]
    missing_execution_paths = [
        item for item in missing_paths
        if item["role"] in execution_required
    ]
    scientific_status = "ready" if not missing_scientific_roles and not missing_scientific_paths and not malformed else "blocked"
    if not args.require_approval:
        execution_gate_status = "not_requested"
    elif missing_execution_roles or missing_execution_paths:
        execution_gate_status = "approval_required" if scientific_status == "ready" else "blocked"
    else:
        execution_gate_status = "approved"
    production_md_gate_approved = scientific_status == "ready" and execution_gate_status == "approved"
    real_submit_allowed = False
    if scientific_status != "ready":
        helper_status = "blocked"
    elif args.require_approval and execution_gate_status != "approved":
        helper_status = "warning"
    else:
        helper_status = "success"
    warnings = [
        {"code": "missing_evidence_role", "message": f"Missing MLP evidence role: {role}"}
        for role in missing_scientific_roles
    ] + [
        {"code": "missing_execution_gate_evidence", "message": f"Missing execution gate evidence role: {role}"}
        for role in missing_execution_roles
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
        status=helper_status,
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
            "Production MLP-MD readiness approval does not authorize real local, remote, or HPC submit.",
        ],
        warnings=warnings,
        limitations=[
            "This validates evidence presence only.",
            "Scientific adequacy requires domain review of the referenced evidence.",
        ],
        production_readiness_requested=args.production_readiness,
        scientific_readiness={
            "status": scientific_status,
            "required_roles": scientific_required,
            "missing_roles": missing_scientific_roles,
            "missing_paths": missing_scientific_paths,
        },
        scientific_readiness_status=scientific_status,
        execution_gate={
            "status": execution_gate_status,
            "gate": "production_md_readiness" if args.production_readiness else "mlp_evidence_presence_review",
            "gate_scope": "production_md_readiness_only" if args.production_readiness else "evidence_presence_only",
            "required_roles": execution_required,
            "missing_roles": missing_execution_roles,
            "missing_paths": missing_execution_paths,
            "production_md_gate_approved": production_md_gate_approved,
            "real_submit_allowed": real_submit_allowed,
        },
        production_md_gate_approved=production_md_gate_approved,
        real_submit_gate={
            "gate": "hpc_submit",
            "status": "required_for_real_submit",
            "reason": "MLP production-readiness approval does not authorize real local, remote, or HPC submit.",
        },
        real_submit_allowed=real_submit_allowed,
        approval_required=args.require_approval,
        required_roles=required,
        provided_roles=sorted(evidence),
        missing_roles=missing_scientific_roles + missing_execution_roles,
        missing_scientific_roles=missing_scientific_roles,
        missing_execution_roles=missing_execution_roles,
        missing_paths=missing_paths,
        malformed_entries=malformed,
        blocked_claims=(
            ["production MLP-MD readiness", "real production MLP-MD execution"]
            if args.production_readiness and scientific_status != "ready"
            else ["real production MLP-MD execution"]
            if args.production_readiness
            else []
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
            "execution_gate": result.get("execution_gate"),
            "production_md_gate_approved": result.get("production_md_gate_approved"),
            "real_submit_gate": result.get("real_submit_gate"),
            "production_readiness": args.production_readiness,
            "approval_required": args.require_approval,
        },
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
