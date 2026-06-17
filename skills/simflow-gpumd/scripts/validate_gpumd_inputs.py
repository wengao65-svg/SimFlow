#!/usr/bin/env python3
"""Validate GPUMD/NEP inputs without running GPUMD or NEP."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from runtime.simflow_core.script_contracts import add_helper_recording_args, maybe_record_helper_run
from runtime.simflow_helpers.engines.gpumd import validate_gpumd_inputs as validate_inputs


def validate_gpumd_inputs(task: str, calc_dir: str, software: str = "gpumd") -> dict:
    """Validate a GPUMD/NEP calculation directory."""
    return validate_inputs(task, calc_dir, software=software)


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate GPUMD/NEP inputs")
    parser.add_argument("--task", required=True)
    parser.add_argument("--calc-dir", default=".")
    parser.add_argument("--software", choices=["gpumd", "nep"], default="gpumd")
    parser.add_argument("--output", default=None)
    add_helper_recording_args(parser, default_stage="computation")
    args = parser.parse_args()

    try:
        result = validate_gpumd_inputs(args.task, args.calc_dir, args.software)
        if args.output:
            output = Path(args.output)
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            result["output_file"] = str(output)
        result = maybe_record_helper_run(
            args=args,
            result=result,
            script_path=Path(__file__).resolve(),
            helper_name="gpumd_validate_inputs",
            software=result.get("software") or args.software,
            input_paths=[args.calc_dir],
            output_paths=[args.output] if args.output else [],
            metadata={"capability": "input_validation", "helper_result_status": result.get("status")},
        )
        print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    except Exception as exc:
        print(json.dumps({"status": "error", "message": str(exc)}, indent=2, ensure_ascii=False))
        sys.exit(1)


if __name__ == "__main__":
    main()
