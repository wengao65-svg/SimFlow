#!/usr/bin/env python3
"""Validate MLP evidence roles without judging scientific quality."""

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
PRODUCTION_REQUIRED = BASE_REQUIRED + [
    "model_metrics_summary",
    "smoke_md_manifest",
    "anomaly_report",
    "active_learning_round_manifest",
]
APPROVAL_REQUIRED = ["approval_record"]
BLOCKING_STATUSES = {"blocked", "block", "failed", "fail", "error", "missing", "incomplete", "capability_warning", "skipped_optional_dependency"}
PRODUCTION_PASS_STATUSES = {"completed", "pass", "passed", "success", "ready"}
BLOCKING_PARSER_STATUSES = {"missing", "malformed", "unrecognized"}


def _read_json_payload(role: str, path_value: str) -> tuple[dict | None, list[dict]]:
    path = Path(path_value).expanduser()
    if path.exists() and not path.is_file():
        return None, [{"role": role, "path": str(path), "code": "non_file_evidence_path", "message": "Evidence path must be a regular JSON file."}]
    if not path.is_file():
        return None, []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, [{"role": role, "path": str(path), "code": "invalid_evidence_json", "message": str(exc)}]
    if not isinstance(payload, dict):
        return None, [{"role": role, "path": str(path), "code": "non_object_evidence", "message": "Evidence JSON must be an object."}]
    if not payload:
        return payload, [{"role": role, "path": str(path), "code": "empty_evidence_json", "message": "Evidence JSON is empty."}]
    return payload, []


def _evidence_path_issue(role: str, path_value: str) -> dict | None:
    path = Path(path_value).expanduser()
    if not path.exists():
        return {"role": role, "path": path_value, "code": "missing_evidence_path", "message": f"Evidence path for {role} does not exist: {path_value}"}
    if not path.is_file():
        return {"role": role, "path": path_value, "code": "non_file_evidence_path", "message": f"Evidence path for {role} must be a regular JSON file: {path_value}"}
    return None


def _status_issue(role: str, payload: dict, *, status_key: str = "status") -> dict | None:
    status = str(payload.get(status_key, "")).strip().lower()
    if not status:
        return {"role": role, "code": f"missing_{status_key}", "message": f"Missing required field: {status_key}."}
    if status in BLOCKING_STATUSES or status == "warning":
        return {"role": role, "code": "non_passing_status", "message": f"{role} has non-passing {status_key}: {status}."}
    if status not in PRODUCTION_PASS_STATUSES:
        return {"role": role, "code": "unknown_status", "message": f"{role} has unrecognized {status_key}: {status}."}
    return None


def _parser_issue(role: str, payload: dict) -> dict | None:
    parser_status = str(payload.get("parser_status", "")).strip().lower()
    if parser_status in BLOCKING_PARSER_STATUSES:
        return {"role": role, "code": "blocking_parser_status", "message": f"{role} has parser_status={parser_status}."}
    return None


def _has_any(payload: dict, keys: tuple[str, ...]) -> bool:
    return any(payload.get(key) not in (None, "", [], {}) for key in keys)


def _has_text(payload: dict, keys: tuple[str, ...]) -> bool:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return True
        if isinstance(value, list) and any(isinstance(item, str) and item.strip() for item in value):
            return True
    return False


def _semantic_issues(role: str, payload: dict) -> list[dict]:
    issues = []
    parser_issue = _parser_issue(role, payload)
    if parser_issue:
        issues.append(parser_issue)

    if role == "dataset_manifest":
        if payload.get("lineage_complete") is not True:
            issues.append({"role": role, "code": "dataset_lineage_incomplete", "message": "dataset_manifest.lineage_complete must be true."})
        if not payload.get("datasets"):
            issues.append({"role": role, "code": "missing_dataset_records", "message": "dataset_manifest.datasets must list source dataset files."})
        return issues

    if role == "labeling_manifest":
        status_issue = _status_issue(role, payload)
        if status_issue:
            issues.append(status_issue)
        if not _has_any(payload, ("label_source", "reference_label_source", "dft_settings", "label_provenance")):
            issues.append({"role": role, "code": "missing_label_provenance", "message": "Label source or DFT label provenance is required."})
        return issues

    if role == "training_run_manifest":
        status_issue = _status_issue(role, payload)
        if status_issue:
            issues.append(status_issue)
        if not _has_any(payload, ("model_artifact", "model_artifacts", "model_file", "model_files")):
            issues.append({"role": role, "code": "missing_model_artifact", "message": "Training evidence must identify model artifact(s)."})
        return issues

    if role == "model_metrics_summary":
        status_issue = _status_issue(role, payload)
        if status_issue:
            issues.append(status_issue)
        has_metrics = _has_any(payload, ("metric_files", "metrics", "threshold_comparisons")) or any(
            isinstance(value, (int, float)) for value in payload.values()
        )
        if not has_metrics:
            issues.append({"role": role, "code": "missing_metrics", "message": "Metrics evidence must contain metric values or metric file summaries."})
        return issues

    if role == "model_validation_report":
        status_issue = _status_issue(role, payload)
        if status_issue:
            issues.append(status_issue)
        if not _has_any(payload, ("validation_domain", "metrics", "rmse_energy_mev_atom", "property_validation")):
            issues.append({"role": role, "code": "missing_validation_context", "message": "Validation evidence must identify the validation domain or metrics."})
        return issues

    if role == "smoke_md_manifest":
        status_issue = _status_issue(role, payload, status_key="smoke_status")
        if status_issue:
            issues.append(status_issue)
        if not _has_any(payload, ("steps", "duration", "trajectory", "run_manifest")):
            issues.append({"role": role, "code": "missing_smoke_md_scope", "message": "Smoke MD evidence must record steps, duration, trajectory, or run manifest."})
        return issues

    if role == "anomaly_report":
        if payload.get("thresholds_defined") is not True:
            issues.append({"role": role, "code": "missing_anomaly_thresholds", "message": "anomaly_report.thresholds_defined must be true."})
        return issues

    if role == "active_learning_round_manifest":
        status_issue = _status_issue(role, payload)
        if status_issue:
            issues.append(status_issue)
        if payload.get("active_learning_used") is False:
            if not _has_text(payload, ("decision_rationale", "rationale", "decision", "reason", "justification")):
                issues.append({
                    "role": role,
                    "code": "missing_active_learning_decision_rationale",
                    "message": "A no-active-learning decision must record its rationale.",
                })
            if not _has_text(payload, ("residual_risk", "residual_risks")):
                issues.append({
                    "role": role,
                    "code": "missing_active_learning_residual_risk",
                    "message": "A no-active-learning decision must record residual risk.",
                })
        elif not _has_any(payload, ("iteration_id", "round", "candidate_pool", "selection_report", "dataset_update", "validation_changes")):
            issues.append({
                "role": role,
                "code": "missing_active_learning_context",
                "message": "Active-learning evidence must record a round context or an explicit no-active-learning decision.",
            })
        return issues

    return issues


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
        issue
        for role, path in evidence.items()
        if path
        for issue in [_evidence_path_issue(role, path)]
        if issue is not None
    ]
    missing_scientific_paths = [
        item for item in missing_paths
        if item["role"] in scientific_required
    ]
    missing_execution_paths = [
        item for item in missing_paths
        if item["role"] in execution_required
    ]
    evidence_payloads = {}
    semantic_issues = []
    if args.production_readiness:
        for role, path in evidence.items():
            if role not in scientific_required or any(item["role"] == role for item in missing_paths):
                continue
            payload, load_issues = _read_json_payload(role, path)
            semantic_issues.extend(load_issues)
            if payload is not None:
                evidence_payloads[role] = payload
                semantic_issues.extend(_semantic_issues(role, payload))
    scientific_status = (
        "ready"
        if not missing_scientific_roles and not missing_scientific_paths and not malformed and not semantic_issues
        else "blocked"
    )
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
        {"code": item.get("code", "missing_evidence_path"), "message": item.get("message", f"Evidence path for {item['role']} is unavailable: {item['path']}")}
        for item in missing_paths
    ] + [
        {"code": "malformed_evidence_entry", "message": f"Evidence entry must use role=path form: {item}"}
        for item in malformed
    ] + [
        {"code": issue["code"], "message": f"{issue['role']}: {issue['message']}"}
        for issue in semantic_issues
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
            "This validates evidence presence and minimum production-readiness fields only.",
            "Scientific adequacy still requires domain review of the referenced evidence.",
            "Approval evidence is conditional and required only when --require-approval is set.",
            "Production MLP-MD readiness approval does not authorize real local, remote, or HPC submit.",
        ],
        warnings=warnings,
        limitations=[
            "This validates evidence presence and minimum production-readiness fields only.",
            "Scientific adequacy still requires domain review of the referenced evidence.",
        ],
        production_readiness_requested=args.production_readiness,
        scientific_readiness={
            "status": scientific_status,
            "required_roles": scientific_required,
            "missing_roles": missing_scientific_roles,
            "missing_paths": missing_scientific_paths,
            "semantic_issues": semantic_issues,
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
        semantic_issues=semantic_issues,
        semantic_blocked_roles=sorted({issue["role"] for issue in semantic_issues}),
        evidence_payload_roles=sorted(evidence_payloads),
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
