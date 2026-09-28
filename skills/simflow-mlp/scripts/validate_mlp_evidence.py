#!/usr/bin/env python3
"""Validate MLP evidence roles without judging scientific quality."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
from metadata import source_file_record


BASE_REQUIRED = ["dataset_manifest", "labeling_manifest", "training_run_manifest", "model_validation_report"]
PRODUCTION_REQUIRED = BASE_REQUIRED + [
    "model_metrics_summary",
    "smoke_md_manifest",
    "anomaly_report",
    "active_learning_round_manifest",
]
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
    parser.add_argument("--output", default=None)
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
    required = scientific_required
    missing_scientific_roles = [role for role in scientific_required if role not in evidence]
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
    if scientific_status != "ready":
        helper_status = "blocked"
    else:
        helper_status = "success"
    warnings = [
        {"code": "missing_evidence_role", "message": f"Missing MLP evidence role: {role}"}
        for role in missing_scientific_roles
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
    result = {
        "helper": "validate_mlp_evidence",
        "capability": "production_mlp_md_readiness_review" if args.production_readiness else "mlp_evidence_presence_review",
        "evidence_role": "production_md_readiness_report" if args.production_readiness else "mlp_evidence_presence_report",
        "status": helper_status,
        "source_files": [source_file_record(path, role=role) for role, path in evidence.items()],
        "parser_status": "parsed" if not missing_paths and not malformed else "partial",
        "claim_limits": [
            "This validates evidence presence and minimum production-readiness fields only.",
            "Scientific adequacy still requires domain review of the referenced evidence.",
            "This report does not grant execution permission; host permissions and user authorization control real execution.",
        ],
        "warnings": warnings,
        "limitations": [
            "This validates evidence presence and minimum production-readiness fields only.",
            "Scientific adequacy still requires domain review of the referenced evidence.",
        ],
        "production_readiness_requested": args.production_readiness,
        "scientific_readiness": {
            "status": scientific_status,
            "required_roles": scientific_required,
            "missing_roles": missing_scientific_roles,
            "missing_paths": missing_scientific_paths,
            "semantic_issues": semantic_issues,
        },
        "scientific_readiness_status": scientific_status,
        "required_roles": required,
        "provided_roles": sorted(evidence),
        "missing_roles": missing_scientific_roles,
        "missing_scientific_roles": missing_scientific_roles,
        "missing_paths": missing_paths,
        "semantic_issues": semantic_issues,
        "semantic_blocked_roles": sorted({issue["role"] for issue in semantic_issues}),
        "evidence_payload_roles": sorted(evidence_payloads),
        "malformed_entries": malformed,
        "blocked_claims": ["production MLP-MD readiness"] if args.production_readiness and scientific_status != "ready" else [],
        "execution_note": "Real execution remains under host permissions and user authorization; this report is an evidence review only.",
    }
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        result["output_file"] = str(output)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
