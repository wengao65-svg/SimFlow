#!/usr/bin/env python3
"""Run the canonical modeling stage for Milestone C."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from build_structure import build_from_file, build_from_params, build_from_type
from make_supercell import make_supercell
from runtime.lib.artifact import register_artifact
from runtime.lib.proposal_contract import load_proposal_contract
from runtime.lib.state import read_state
from validate_structure import validate_structure


def resolve_project_root_from_workflow_dir(workflow_dir: str) -> Path:
    """Resolve the project root from either a project root or .simflow path."""
    path = Path(workflow_dir).expanduser().resolve()
    return path.parent if path.name == ".simflow" else path


def _parse_supercell(value: Any) -> list[int] | None:
    if value in (None, "", False):
        return None
    if isinstance(value, str):
        parts = value.lower().replace("×", "x").split("x")
        if len(parts) == 3 and all(part.strip().isdigit() for part in parts):
            return [int(part.strip()) for part in parts]
    if isinstance(value, (list, tuple)) and len(value) == 3:
        return [int(item) for item in value]
    raise ValueError(f"Unsupported supercell specification: {value}")


def _resolve_structure_spec(project_root: Path, contract: dict[str, Any], params: dict[str, Any]) -> dict[str, Any]:
    overrides = contract.get("parameter_overrides", {})
    hints = contract.get("structure_hints", {})
    merged = {**overrides, **hints, **(params or {})}

    file_candidate = merged.get("structure_file") or merged.get("structure_path") or merged.get("cif") or merged.get("poscar")
    if file_candidate:
        structure_path = Path(file_candidate).expanduser()
        resolved = structure_path if structure_path.is_absolute() else project_root / structure_path
        return {"mode": "existing_file", "path": resolved}

    structure_type = merged.get("structure_type")
    lattice_param = merged.get("lattice_param")
    elements = merged.get("elements")
    if structure_type and lattice_param and elements:
        if isinstance(elements, str):
            elements = [item.strip() for item in elements.split(",") if item.strip()]
        return {
            "mode": "from_type",
            "structure_type": str(structure_type),
            "lattice_param": float(lattice_param),
            "elements": list(elements),
        }

    coords = merged.get("coords")
    explicit_lattice = all(key in merged for key in ("a", "b", "c", "elements", "coords"))
    if explicit_lattice:
        parsed_coords = coords
        if isinstance(coords, str):
            parsed_coords = json.loads(coords)
        elements = merged["elements"]
        if isinstance(elements, str):
            try:
                parsed_elements = json.loads(elements)
                elements = parsed_elements if isinstance(parsed_elements, list) else [elements]
            except json.JSONDecodeError:
                elements = [item.strip() for item in elements.split(",") if item.strip()]
        return {
            "mode": "from_params",
            "a": float(merged["a"]),
            "b": float(merged["b"]),
            "c": float(merged["c"]),
            "alpha": float(merged.get("alpha", 90.0)),
            "beta": float(merged.get("beta", 90.0)),
            "gamma": float(merged.get("gamma", 90.0)),
            "elements": list(elements),
            "coords": parsed_coords,
            "fractional": bool(merged.get("fractional", True)),
        }

    return {"mode": "planning_only", "reason": "No explicit structure hints were provided in the proposal contract."}


def _write_structure_from_spec(spec: dict[str, Any], output_path: Path) -> dict[str, Any]:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if spec["mode"] == "existing_file":
        structure = build_from_file(str(spec["path"]))
        structure.to(filename=str(output_path), fmt="poscar")
        return {"source_mode": "existing_file", "source_path": str(spec["path"]), "output_path": str(output_path)}

    if spec["mode"] == "from_type":
        structure = build_from_type(spec["structure_type"], spec["lattice_param"], spec["elements"])
        structure.to(filename=str(output_path), fmt="poscar")
        return {
            "source_mode": "from_type",
            "structure_type": spec["structure_type"],
            "lattice_param": spec["lattice_param"],
            "elements": spec["elements"],
            "output_path": str(output_path),
        }

    if spec["mode"] == "from_params":
        structure = build_from_params(
            spec["a"], spec["b"], spec["c"], spec["alpha"], spec["beta"], spec["gamma"],
            spec["elements"], spec["coords"], spec["fractional"],
        )
        structure.to(filename=str(output_path), fmt="poscar")
        return {
            "source_mode": "from_params",
            "elements": spec["elements"],
            "output_path": str(output_path),
        }

    raise ValueError(f"Unsupported structure spec mode: {spec['mode']}")


def run_modeling_stage(workflow_dir: str, params: dict | None = None, dry_run: bool = False) -> dict:
    """Run the canonical modeling stage and register artifacts."""
    project_root = resolve_project_root_from_workflow_dir(workflow_dir)
    state = read_state(project_root=str(project_root), state_file="workflow.json")
    if not state:
        return {"status": "error", "message": "No workflow state found"}

    params = params or {}
    contract = load_proposal_contract(str(project_root / ".simflow"))
    proposal_artifact_ids = [artifact["artifact_id"] for artifact in contract["proposal_artifacts"].values()]
    spec = _resolve_structure_spec(project_root, contract, params)
    supercell = _parse_supercell(params.get("supercell") or contract.get("parameter_overrides", {}).get("supercell"))

    manifest: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "workflow_type": contract["workflow_type"],
        "software": contract["software"],
        "material": contract["material"],
        "proposal_artifact_ids": proposal_artifact_ids,
        "research_question_ids": [item["question_id"] for item in contract.get("research_questions", [])],
        "supercell": supercell,
        "status": "planned" if dry_run else "completed",
    }

    if spec["mode"] == "planning_only":
        manifest.update({
            "source_mode": "planning_only",
            "structure_files": [],
            "validation": None,
            "notes": [spec["reason"]],
        })
    elif dry_run:
        manifest.update({
            "source_mode": spec["mode"],
            "structure_files": [".simflow/artifacts/modeling/POSCAR"],
            "validation": "would_run",
            "notes": ["Dry-run only; no structure files were created."],
        })
    else:
        artifacts_dir = project_root / ".simflow" / "artifacts" / "modeling"
        reports_dir = project_root / ".simflow" / "reports" / "modeling"
        structure_path = artifacts_dir / "POSCAR"
        write_info = _write_structure_from_spec(spec, structure_path)
        final_structure_path = structure_path
        if supercell:
            supercell_path = artifacts_dir / "POSCAR_supercell"
            make_supercell(str(structure_path), supercell, str(supercell_path), fmt="poscar")
            final_structure_path = supercell_path
        validation = validate_structure(str(final_structure_path))
        manifest.update({
            **write_info,
            "structure_files": [str(final_structure_path.resolve().relative_to(project_root))],
            "validation": validation,
        })
        reports_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = reports_dir / "structure_manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

        manifest_artifact = register_artifact(
            "structure_manifest.json",
            "structure_manifest",
            "modeling",
            project_root=str(project_root),
            path=str(manifest_path.resolve().relative_to(project_root)),
            parent_artifacts=proposal_artifact_ids,
            parameters={"source_mode": manifest["source_mode"]},
            software=contract["software"],
        )
        structure_artifact = register_artifact(
            Path(final_structure_path).name,
            "structure",
            "modeling",
            project_root=str(project_root),
            path=str(final_structure_path.resolve().relative_to(project_root)),
            parent_artifacts=[manifest_artifact["artifact_id"]],
            parameters={"supercell": supercell},
            software=contract["software"],
        )
        return {
            "status": "success",
            "artifacts": [manifest_artifact, structure_artifact],
            "manifest": manifest,
            "inputs": proposal_artifact_ids,
        }

    reports_dir = project_root / ".simflow" / "reports" / "modeling"
    reports_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = reports_dir / "structure_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    if dry_run:
        return {
            "status": "dry_run_complete",
            "manifest": manifest,
            "inputs": proposal_artifact_ids,
            "planned_outputs": [".simflow/reports/modeling/structure_manifest.json"],
        }

    manifest_artifact = register_artifact(
        "structure_manifest.json",
        "structure_manifest",
        "modeling",
        project_root=str(project_root),
        path=str(manifest_path.resolve().relative_to(project_root)),
        parent_artifacts=proposal_artifact_ids,
        parameters={"source_mode": manifest["source_mode"]},
        software=contract["software"],
    )
    return {
        "status": "success",
        "artifacts": [manifest_artifact],
        "manifest": manifest,
        "inputs": proposal_artifact_ids,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the canonical modeling stage")
    parser.add_argument("--workflow-dir", required=True, help="Path to .simflow directory")
    parser.add_argument("--params", type=str, default="{}", help="JSON parameters for the stage")
    parser.add_argument("--dry-run", action="store_true", default=False)
    args = parser.parse_args()

    try:
        params = json.loads(args.params)
        result = run_modeling_stage(args.workflow_dir, params=params, dry_run=args.dry_run)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except Exception as exc:
        print(json.dumps({"status": "error", "message": str(exc)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
