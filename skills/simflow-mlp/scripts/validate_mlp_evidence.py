#!/usr/bin/env python3
"""Validate presence of MLP evidence roles without judging scientific quality."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

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
    status = "ready" if not missing_roles and not missing_paths and not malformed else "blocked"
    result = {
        "status": status,
        "production_readiness_requested": args.production_readiness,
        "approval_required": args.require_approval,
        "required_roles": required,
        "provided_roles": sorted(evidence),
        "missing_roles": missing_roles,
        "missing_paths": missing_paths,
        "malformed_entries": malformed,
        "blocked_claims": (
            ["production MLP-MD readiness"] if args.production_readiness and status != "ready" else []
        ),
        "limitations": [
            "This validates evidence presence only.",
            "Scientific adequacy requires domain review of the referenced evidence.",
        ],
    }
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
            "production_readiness": args.production_readiness,
            "approval_required": args.require_approval,
        },
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
