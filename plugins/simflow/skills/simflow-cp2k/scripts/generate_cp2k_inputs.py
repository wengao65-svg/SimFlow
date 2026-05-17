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

from _common import ensure_cp2k_project, finalize_stage, register_report, write_json_verified
from runtime.lib.cp2k_input import extract_last_frame, generate_input, normalize_calc_type, read_cif_to_xyz, read_xyz_structure, write_xyz


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
    root, state = ensure_cp2k_project(project_root, "input_generation")
    work_dir = (root / calc_dir).resolve()
    work_dir.mkdir(parents=True, exist_ok=True)

    structure = Path(structure_path).expanduser().resolve()
    if not structure.is_file():
        raise FileNotFoundError(f"Structure file not found: {structure_path}")

    coord_name = params.get("coord_file")
    structure_report = {
        "source_structure": str(structure),
        "task": task_norm,
        "calc_dir": str(work_dir),
    }

    generation_params = dict(params)
    if structure.suffix.lower() == ".cif":
        cell_abc, xyz_lines, element_counts = read_cif_to_xyz(structure)
        coord_name = coord_name or "structure.xyz"
        coord_path = work_dir / coord_name
        coord_path.write_text(write_xyz(len(xyz_lines), f"Generated from {structure.name}", xyz_lines), encoding="utf-8")
        parts = cell_abc.split()
        generation_params.update({
            "cell_a": parts[0],
            "cell_b": parts[1],
            "cell_c": parts[2],
            "coord_file": coord_name,
            "coord_format": "XYZ",
            "elements": sorted(element_counts),
            "coord_path": str(coord_path),
        })
        structure_report["element_counts"] = element_counts
        structure_report["cell_abc"] = cell_abc
    elif structure.suffix.lower() == ".xyz":
        content = structure.read_text(encoding="utf-8")
        if task_norm == "energy":
            normalized_xyz = extract_last_frame(content)
            coord_name = coord_name or "last_frame.xyz"
        else:
            atom_lines, _, comment = read_xyz_structure(structure)
            normalized_xyz = write_xyz(len(atom_lines), comment or f"Generated from {structure.name}", atom_lines)
            coord_name = coord_name or "structure.xyz"
        coord_path = work_dir / coord_name
        coord_path.write_text(normalized_xyz, encoding="utf-8")
        _, element_counts, _ = read_xyz_structure(coord_path)
        generation_params.update({
            "coord_file": coord_name,
            "coord_format": "XYZ",
            "elements": sorted(element_counts),
            "coord_path": str(coord_path),
        })
        structure_report["element_counts"] = element_counts
    else:
        raise ValueError(f"Unsupported structure format: {structure.suffix}")

    input_text = generate_input(generation_params, task_norm)
    input_name = f"{task_norm}.inp"
    input_path = work_dir / input_name
    input_path.write_text(input_text, encoding="utf-8")

    report = {
        "status": "success",
        "task": task_norm,
        "input_file": str(input_path),
        "coordinate_file": str(coord_path),
        "parameters": {
            "coord_file": coord_name,
            "elements": generation_params.get("elements", []),
            "project_name": generation_params.get("project_name"),
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
    artifacts = [
        register_report(root, "input_generation", task_norm, "generation_report", files["generation_report"]),
        register_report(root, "input_generation", task_norm, "handoff_artifact", files["handoff_artifact"], artifact_type="handoff"),
    ]
    checkpoint = finalize_stage(
        root,
        state,
        "input_generation",
        task_norm,
        files,
        "success",
        f"Generated CP2K inputs for {task_norm}.",
    )

    return {
        "status": "success",
        "task": task_norm,
        "files_generated": [str(input_path), str(coord_path)],
        "reports": files,
        "artifacts": artifacts,
        "checkpoint": checkpoint,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate common-task CP2K inputs inside a SimFlow project")
    parser.add_argument("--structure", required=True, help="Path to CIF or XYZ structure file")
    parser.add_argument("--task", required=True, help="CP2K task: energy, geo_opt, cell_opt, aimd_nvt, aimd_nve, aimd_npt")
    parser.add_argument("--project-root", required=True, help="User project root for .simflow and reports")
    parser.add_argument("--calc-dir", default=".", help="Calculation directory relative to project_root")
    parser.add_argument("--params", default="{}", help="JSON parameter overrides")
    args = parser.parse_args()

    try:
        result = generate_cp2k_inputs(
            structure_path=args.structure,
            task=args.task,
            project_root=args.project_root,
            calc_dir=args.calc_dir,
            params=json.loads(args.params),
        )
        print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    except Exception as exc:
        print(json.dumps({"status": "error", "message": str(exc)}, indent=2, ensure_ascii=False))
        sys.exit(1)


if __name__ == "__main__":
    main()
