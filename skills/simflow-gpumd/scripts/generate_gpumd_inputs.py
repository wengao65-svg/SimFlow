#!/usr/bin/env python3
"""Generate bounded GPUMD/NEP inputs without executing GPUMD or NEP."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from runtime.simflow_core.script_contracts import add_helper_recording_args, maybe_record_helper_run
from runtime.simflow_core.toolchains import build_actual_tool_used, classify_tool_support
from runtime.simflow_helpers.engines.gpumd import generate_gpumd_inputs as generate_inputs


def generate_gpumd_inputs(
    structure_path: str | None,
    task: str,
    project_root: str,
    calc_dir: str = ".",
    params: dict | None = None,
    software: str = "gpumd",
) -> dict:
    """Generate GPUMD/NEP input files into a calculation directory."""
    root = Path(project_root).expanduser().resolve()
    work_dir = (root / calc_dir).resolve()
    params = dict(params or {})
    result = generate_inputs(
        structure_path,
        task,
        str(work_dir),
        project_root=str(root),
        params=params,
        software=software,
    )
    support = classify_tool_support([result.get("software") or software])
    result["actual_tool_used"] = build_actual_tool_used(
        {"software": result.get("software") or software, "helper_support": support},
        result.get("software") or software,
    )
    result["calc_dir"] = str(work_dir)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate bounded GPUMD/NEP input files")
    parser.add_argument("--structure", default=None, help="Structure file for GPUMD model.xyz generation")
    parser.add_argument("--task", required=True, help="GPUMD/NEP task")
    parser.add_argument("--project-root", required=True, help="Project root")
    parser.add_argument("--calc-dir", default=".", help="Calculation directory relative to project_root")
    parser.add_argument("--software", choices=["gpumd", "nep"], default="gpumd")
    parser.add_argument("--params", default="{}", help="JSON parameter overrides")
    add_helper_recording_args(parser, default_stage="computation")
    args = parser.parse_args()

    try:
        result = generate_gpumd_inputs(
            args.structure,
            args.task,
            args.project_root,
            calc_dir=args.calc_dir,
            params=json.loads(args.params),
            software=args.software,
        )
        result = maybe_record_helper_run(
            args=args,
            result=result,
            script_path=Path(__file__).resolve(),
            helper_name="gpumd_generate_inputs",
            software=result.get("software") or args.software,
            input_paths=[args.structure] if args.structure else [],
            output_paths=result.get("files_generated", []),
            metadata={"capability": "input_generation", "helper_result_status": result.get("status")},
        )
        print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    except Exception as exc:
        print(json.dumps({"status": "error", "message": str(exc)}, indent=2, ensure_ascii=False))
        sys.exit(1)


if __name__ == "__main__":
    main()
