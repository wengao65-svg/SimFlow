#!/usr/bin/env python3
"""Record user-provided computation evidence for tracked-only tools."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from runtime.simflow_core.script_contracts import add_helper_recording_args, maybe_record_helper_run
from runtime.simflow_helpers.computation.evidence_intake import record_computation_evidence


def main() -> None:
    parser = argparse.ArgumentParser(description="Record generic computation evidence")
    parser.add_argument("--workflow-dir", required=True, help="Path to .simflow directory")
    parser.add_argument("--params", type=str, default="{}", help="JSON evidence intake parameters")
    parser.add_argument("--dry-run", action="store_true", default=False)
    add_helper_recording_args(parser, default_stage="computation")
    args = parser.parse_args()

    try:
        params = json.loads(args.params)
        result = record_computation_evidence(args.workflow_dir, params=params, dry_run=args.dry_run)
        result = maybe_record_helper_run(
            args=args,
            result=result,
            script_path=Path(__file__).resolve(),
            helper_name="record_computation_evidence",
            metadata={"dry_run": args.dry_run, "helper_result_status": result.get("status")},
            software=params.get("software"),
        )
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except Exception as exc:
        print(json.dumps({"status": "error", "message": str(exc)}, indent=2, ensure_ascii=False))
        sys.exit(1)


if __name__ == "__main__":
    main()
