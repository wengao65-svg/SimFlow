#!/usr/bin/env python3
"""Generate common-task CP2K inputs inside a SimFlow project."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from _common import resolve_cp2k_paths, write_json_verified
from runtime.simflow_core.result_contract import attach_simflow_result
from runtime.simflow_core.script_contracts import add_helper_recording_args, maybe_record_helper_run
from runtime.simflow_helpers.engines.cp2k_input import generate_cp2k_input_package, normalize_calc_type


def generate_cp2k_inputs(
    structure_path: str,
    task: str,
    project_root: str,
    calc_dir: str = ".",
    params: dict | None = None,
) -> dict:
    """Generate a CP2K input deck and normalized coordinate file."""
    task_norm = normalize_calc_type(task)
    params = dict(params or {})
    stage = "computation"
    activity = "input_generation"
    root, work_dir = resolve_cp2k_paths(project_root, calc_dir)
    work_dir.mkdir(parents=True, exist_ok=True)

    structure = Path(structure_path).expanduser().resolve()
    if not structure.is_file():
        raise FileNotFoundError(f"Structure file not found: {structure_path}")

    generated = generate_cp2k_input_package(structure, task_norm, work_dir, params=params)
    input_path = Path(generated["input_file"])
    coord_path = Path(generated["coordinate_file"])
    coord_name = generated["parameters"]["coord_file"]
    structure_report = generated["structure"]

    report = {
        "status": "success",
        "task": task_norm,
        "input_file": str(input_path),
        "coordinate_file": str(coord_path),
        "parameters": {
            "coord_file": coord_name,
            "elements": sorted(generated["parameters"].get("elements", {})),
            "project_name": params.get("project_name"),
        },
        "structure": structure_report,
    }
    handoff = {
        "task": task_norm,
        "generated_files": [str(input_path.relative_to(root)), str(coord_path.relative_to(root))],
        "next_steps": [
            "Run validate_cp2k_inputs.py or orchestrate_cp2k_task.py against the generated deck.",
            "Review referenced basis/potential library names in the input deck.",
        ],
        "approval_needed": False,
    }

    files = {
        "generation_report": write_json_verified(root, "reports/cp2k/generated_inputs.json", report),
        "handoff_artifact": write_json_verified(root, "reports/cp2k/handoff_artifact.json", handoff),
    }
    result = {
        "status": "success",
        "task": task_norm,
        "files_generated": [str(input_path), str(coord_path)],
        "reports": files,
    }
    return attach_simflow_result(
        result,
        role="helper",
        activity=activity,
        legacy_status=result["status"],
        stage=stage,
        state_effect="none",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate common-task CP2K inputs inside a SimFlow project")
    parser.add_argument("--structure", required=True, help="Path to CIF or XYZ structure file")
    parser.add_argument("--task", required=True, help="CP2K task: energy, geo_opt, cell_opt, aimd_nvt, aimd_nve, aimd_npt")
    parser.add_argument("--project-root", required=True, help="User project root for .simflow and reports")
    parser.add_argument("--calc-dir", default=".", help="Calculation directory relative to project_root")
    parser.add_argument("--params", default="{}", help="JSON parameter overrides")
    add_helper_recording_args(parser, default_stage="computation")
    args = parser.parse_args()

    try:
        result = generate_cp2k_inputs(
            structure_path=args.structure,
            task=args.task,
            project_root=args.project_root,
            calc_dir=args.calc_dir,
            params=json.loads(args.params),
        )
        result = maybe_record_helper_run(
            args=args,
            result=result,
            script_path=Path(__file__).resolve(),
            helper_name="cp2k_generate_inputs",
            software="cp2k",
            input_paths=[args.structure],
            output_paths=result.get("files_generated", []),
        )
        print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    except Exception as exc:
        print(json.dumps({"status": "error", "message": str(exc)}, indent=2, ensure_ascii=False))
        sys.exit(1)


if __name__ == "__main__":
    main()
