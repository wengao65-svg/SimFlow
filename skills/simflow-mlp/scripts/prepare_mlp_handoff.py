#!/usr/bin/env python3
"""Prepare a generic MLP evidence handoff package."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
from metadata import source_file_record

PRODUCTION_HANDOFF_ROLES = [
    "dataset_manifest",
    "labeling_manifest",
    "training_run_manifest",
    "model_metrics_summary",
    "model_validation_report",
    "smoke_md_manifest",
    "anomaly_report",
    "active_learning_round_manifest",
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare MLP evidence handoff JSON")
    parser.add_argument("--evidence", action="append", default=[], help="role=path evidence entry")
    parser.add_argument("--output", required=True)
    parser.add_argument("--goal", default=None)
    parser.add_argument("--toolchain", default=None)
    parser.add_argument("--iteration-id", default=None)
    parser.add_argument("--risk", action="append", default=[])
    parser.add_argument("--next-action", action="append", default=[])
    args = parser.parse_args()

    evidence = []
    for item in args.evidence:
        if "=" not in item:
            evidence.append({"role": None, "path": item, "present": Path(item).expanduser().exists(), "warning": "missing role"})
            continue
        role, path = item.split("=", 1)
        evidence.append({"role": role.strip(), "path": path.strip(), "present": Path(path.strip()).expanduser().exists()})
    degraded = any((not item.get("present")) or item.get("warning") for item in evidence)
    provided_roles = sorted({item["role"] for item in evidence if item.get("role")})
    missing_production_roles = [role for role in PRODUCTION_HANDOFF_ROLES if role not in provided_roles]
    warnings = [
        {"code": "missing_evidence_role", "message": f"Evidence entry is missing a role: {item['path']}"}
        for item in evidence
        if item.get("warning")
    ] + [
        {"code": "missing_evidence_path", "message": f"Evidence path does not exist: {item['path']}"}
        for item in evidence
        if item.get("path") and not item.get("present")
    ]
    handoff = {
        "helper": "prepare_mlp_handoff",
        "capability": "evidence_handoff",
        "evidence_role": "mlp_handoff",
        "status": "blocked" if not evidence else ("warning" if degraded else "success"),
        "source_files": [source_file_record(item["path"], role=item.get("role")) for item in evidence if item.get("path")],
        "parser_status": "missing" if not evidence else ("partial" if degraded else "parsed"),
        "claim_limits": [
            "This handoff records evidence presence and provenance.",
            "It does not execute training, certify model quality, or authorize real local, remote, or HPC submit.",
        ],
        "warnings": warnings,
        "limitations": [
            "This handoff records evidence presence and provenance.",
            "Production MLP-MD readiness remains blocked until all required evidence roles and approval evidence are present.",
        ],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "recipe": "mlp_md",
        "goal": args.goal,
        "iteration_id": args.iteration_id,
        "toolchain": [item.strip() for item in args.toolchain.split(",")] if args.toolchain else [],
        "evidence": evidence,
        "provided_roles": provided_roles,
        "missing_production_roles": missing_production_roles,
        "blocked_claims": ["production MLP-MD readiness"] if missing_production_roles or degraded or not evidence else [],
        "risks": args.risk,
        "next_actions": args.next_action,
        "execution_note": "Real execution remains under host permissions and user authorization; this handoff does not execute or authorize it.",
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(handoff, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    handoff["output_file"] = str(output)
    print(json.dumps(handoff, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
