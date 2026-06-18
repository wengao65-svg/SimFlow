#!/usr/bin/env python3
"""Run the canonical input generation stage for Milestone C."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pymatgen.core import Structure

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from runtime.simflow_core.artifacts import get_artifact, register_artifact
from runtime.simflow_core.proposals import (
    STRUCTURE_HINT_KEYS,
    TASK_KEYS,
    load_proposal_contract,
)
from runtime.simflow_core.state import read_state
from runtime.simflow_core.toolchains import (
    build_actual_tool_used,
    capability_warning,
)
from runtime.simflow_helpers.engines.cp2k import normalize_cp2k_task
from runtime.simflow_helpers.engines.gpumd import normalize_gpumd_task

VASP_TASK_ALIASES = {
    "static": "scf",
    "single_point": "scf",
    "singlepoint": "scf",
    "single point": "scf",
    "relaxation": "relax",
    "geometry optimization": "relax",
    "geometry_optimization": "relax",
    "band": "bands",
    "band_structure": "bands",
    "band structure": "bands",
    "aimd": "md",
}


def resolve_project_root_from_workflow_dir(workflow_dir: str) -> Path:
    path = Path(workflow_dir).expanduser().resolve()
    return path.parent if path.name == ".simflow" else path


def _load_function(relative_script: str, function_name: str, module_name: str):
    script_path = ROOT / relative_script
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return getattr(module, function_name)


GENERATE_VASP_INPUTS = _load_function(
    "skills/simflow-vasp/scripts/generate_vasp_inputs.py",
    "generate_vasp_inputs",
    "simflow_vasp_inputs",
)
GENERATE_CP2K_INPUTS = _load_function(
    "skills/simflow-computation/scripts/generate_cp2k_inputs.py",
    "generate_cp2k_inputs",
    "simflow_cp2k_inputs",
)
GENERATE_LAMMPS_INPUTS = _load_function(
    "skills/simflow-lammps/scripts/generate_lammps_inputs.py",
    "generate_lammps_inputs",
    "simflow_lammps_inputs",
)
GENERATE_GPUMD_INPUTS = _load_function(
    "skills/simflow-gpumd/scripts/generate_gpumd_inputs.py",
    "generate_gpumd_inputs",
    "simflow_gpumd_inputs",
)


def _stage_output_artifacts(project_root: Path, stage_name: str) -> list[dict[str, Any]]:
    stages_state = read_state(project_root=str(project_root), state_file="stages.json")
    output_ids = stages_state.get(stage_name, {}).get("outputs", [])
    artifacts = []
    for artifact_id in output_ids:
        artifact = get_artifact(artifact_id, project_root=str(project_root))
        if artifact:
            artifacts.append(artifact)
    return artifacts


def _relative_path(project_root: Path, path: Path) -> str:
    return str(path.resolve().relative_to(project_root))


def _normalize_vasp_task(task: str | None) -> str:
    if not task:
        return "scf"
    normalized = task.strip().lower().replace("-", "_")
    return VASP_TASK_ALIASES.get(normalized, normalized).replace("_", "-") if normalized == "vc_relax" else VASP_TASK_ALIASES.get(normalized, normalized)


def _normalize_task(software: str, task: str | None) -> str:
    if software == "cp2k":
        return normalize_cp2k_task(task or "energy")
    if software == "lammps":
        aliases = {
            "relax": "minimize",
            "relaxation": "minimize",
            "min": "minimize",
            "equilibrate": "nvt",
            "equilibration": "nvt",
            "production": "nve",
            "md": "nve",
        }
        normalized = (task or "minimize").strip().lower().replace("-", "_")
        return aliases.get(normalized, normalized)
    if software in {"gpumd", "nep"}:
        return normalize_gpumd_task(task, software=software)
    return _normalize_vasp_task(task)


def _stage_parameters(contract: dict[str, Any], params: dict[str, Any]) -> dict[str, Any]:
    merged = {**contract.get("parameter_overrides", {}), **(params or {})}
    excluded = set(STRUCTURE_HINT_KEYS) | set(TASK_KEYS) | {
        "workflow_type",
        "software",
        "material",
        "supercell",
        "kppa",
        "scheduler",
        "partition",
        "queue",
        "account",
        "modules",
        "mpi_launcher",
        "pre_commands",
        "potcar_root",
        "use_vaspkit",
        "pair_style",
        "pair_coeff",
        "force_field_source",
        "potential_files",
        "force_field_files",
    }
    return {key: value for key, value in merged.items() if key not in excluded}


def _lammps_generation_params(contract: dict[str, Any], params: dict[str, Any]) -> dict[str, Any]:
    return {**contract.get("parameter_overrides", {}), **(params or {})}


def _missing_lammps_generation_inputs(merged: dict[str, Any]) -> list[str]:
    missing = []
    if not merged.get("pair_coeff"):
        missing.append("pair_coeff")
    if not merged.get("force_field_source") and not merged.get("potential_files") and not merged.get("force_field_files"):
        missing.append("force_field_source")
    return missing


def _as_path_values(value: Any) -> list[str]:
    if value in (None, "", False):
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [str(item) for item in value.values() if item]
    if isinstance(value, (list, tuple)):
        paths: list[str] = []
        for item in value:
            if isinstance(item, dict) and item.get("path"):
                paths.append(str(item["path"]))
            elif item:
                paths.append(str(item))
        return paths
    return []


def _direct_input_file_values(contract: dict[str, Any], params: dict[str, Any]) -> list[str]:
    merged = {**contract.get("parameter_overrides", {}), **(params or {})}
    values: list[str] = []
    for key in (
        "input_files",
        "existing_input_files",
        "calculation_inputs",
        "vasp_input_files",
        "cp2k_input_files",
        "gpumd_input_files",
        "nep_input_files",
    ):
        values.extend(_as_path_values(merged.get(key)))
    input_dir = merged.get("input_dir") or merged.get("calculation_dir")
    if input_dir:
        values.append(str(input_dir))
    return list(dict.fromkeys(values))


def _resolve_direct_input_files(project_root: Path, values: list[str]) -> list[Path]:
    resolved: list[Path] = []
    for value in values:
        path = Path(value).expanduser()
        path = path if path.is_absolute() else project_root / path
        if path.is_dir():
            for child_name in ("INCAR", "KPOINTS", "POSCAR", "POTCAR", "input.inp", "structure.cif"):
                child = path / child_name
                if child.is_file():
                    resolved.append(child.resolve())
            continue
        if path.is_file():
            resolved.append(path.resolve())
    return list(dict.fromkeys(resolved))


def _common_artifact_dir(project_root: Path, files: list[Path]) -> str:
    if not files:
        return "."
    parents = [path.parent for path in files]
    common = Path(os.path.commonpath([str(parent) for parent in parents]))
    try:
        return str(common.resolve().relative_to(project_root))
    except ValueError:
        return str(common.resolve())


def _direct_input_manifest(
    project_root: Path,
    contract: dict[str, Any],
    params: dict[str, Any],
    dry_run: bool,
) -> dict[str, Any] | None:
    input_files = _resolve_direct_input_files(project_root, _direct_input_file_values(contract, params))
    if not input_files:
        return None

    software = contract["software"]
    task = _normalize_task(software, params.get("task") or params.get("job_type") or contract.get("task") or contract.get("job_type"))
    generated_files = [_relative_path(project_root, path) for path in input_files]
    artifact_dir = _common_artifact_dir(project_root, input_files)
    required_names = {path.name for path in input_files}
    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "software": software,
        "task": task,
        "actual_tool_used": build_actual_tool_used(contract, software),
        "status": "planned" if dry_run else "completed",
        "source": "user_provided_input_files",
        "parent_artifact_ids": [],
        "generated_files": generated_files,
        "input_files": generated_files,
        "artifact_dir": artifact_dir,
        "missing_optional_inputs": ["POTCAR"] if software == "vasp" and "POTCAR" not in required_names else [],
        "downstream_compute_hints": {
            "recommended_scheduler": params.get("scheduler", "slurm"),
            "software": software,
            "task": task,
        },
    }
    if software == "vasp":
        manifest.setdefault("num_atoms", int(params.get("num_atoms") or contract.get("parameter_overrides", {}).get("num_atoms") or 1))
        manifest.setdefault("elements", params.get("elements") or contract.get("parameter_overrides", {}).get("elements") or [])
        manifest.setdefault("kpoints_mesh", params.get("kpoints_mesh") or [1, 1, 1])
        manifest.setdefault("potcar", {"status": "not_redistributed"})
    return manifest


def _materialize_cp2k_structure(source_path: Path, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if source_path.suffix.lower() == ".cif":
        shutil.copy2(source_path, output_path)
        return output_path
    structure = Structure.from_file(str(source_path))
    structure.to(filename=str(output_path), fmt="cif")
    return output_path


def run_input_generation_stage(workflow_dir: str, params: dict | None = None, dry_run: bool = True) -> dict:
    project_root = resolve_project_root_from_workflow_dir(workflow_dir)
    state = read_state(project_root=str(project_root), state_file="workflow.json")
    if not state:
        return {"status": "error", "message": "No workflow state found"}

    params = params or {}
    contract = load_proposal_contract(str(project_root / ".simflow"), allow_direct_entry=True)
    modeling_artifacts = _stage_output_artifacts(project_root, "modeling")
    if not modeling_artifacts:
        direct_manifest = _direct_input_manifest(project_root, contract, params, dry_run)
        if not direct_manifest:
            return {"status": "error", "message": "Modeling stage has no registered outputs"}
        if dry_run:
            direct_manifest["planned_outputs"] = [".simflow/reports/input_generation/input_manifest.json"]
            return {
                "status": "dry_run_complete",
                "manifest": direct_manifest,
                "inputs": [],
                "planned_outputs": direct_manifest["planned_outputs"],
            }
        reports_dir = project_root / ".simflow" / "reports" / "input_generation"
        reports_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = reports_dir / "input_manifest.json"
        manifest_path.write_text(json.dumps(direct_manifest, indent=2, ensure_ascii=False), encoding="utf-8")
        manifest_artifact = register_artifact(
            "input_manifest.json",
            "input_manifest",
            "computation",
            project_root=str(project_root),
            path=_relative_path(project_root, manifest_path),
            parent_artifacts=[],
            parameters={"software": direct_manifest["software"], "task": direct_manifest["task"]},
            software=direct_manifest["software"],
            metadata={
                "source": "user_provided_input_files",
                "actual_tool_used": direct_manifest.get("actual_tool_used"),
                "execution_mode": "dry_run" if dry_run else "completed",
            },
        )
        file_artifacts = [
            register_artifact(
                Path(rel_path).name,
                "input_files",
                "computation",
                project_root=str(project_root),
                path=rel_path,
                parent_artifacts=[manifest_artifact["artifact_id"]],
                parameters={"software": direct_manifest["software"], "task": direct_manifest["task"]},
                software=direct_manifest["software"],
                metadata={
                    "source": "user_provided",
                    "actual_tool_used": direct_manifest.get("actual_tool_used"),
                    "execution_mode": "completed",
                },
            )
            for rel_path in direct_manifest["generated_files"]
        ]
        return {
            "status": "success",
            "artifacts": [manifest_artifact, *file_artifacts],
            "manifest": direct_manifest,
            "inputs": [],
        }

    structure_artifact = next((artifact for artifact in modeling_artifacts if artifact.get("type") == "structure"), None)
    structure_manifest_artifact = next((artifact for artifact in modeling_artifacts if artifact.get("type") == "structure_manifest"), None)
    if not structure_artifact or not structure_manifest_artifact:
        return {"status": "error", "message": "Modeling stage outputs are incomplete"}

    software = contract["software"]
    task = _normalize_task(software, params.get("task") or params.get("job_type") or contract.get("task") or contract.get("job_type"))
    structure_path = project_root / structure_artifact["path"]
    stage_params = _stage_parameters(contract, params)
    artifacts_dir = project_root / ".simflow" / "artifacts" / "input_generation"
    reports_dir = project_root / ".simflow" / "reports" / "input_generation"
    parent_artifact_ids = [artifact["artifact_id"] for artifact in modeling_artifacts]

    manifest: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "software": software,
        "task": task,
        "actual_tool_used": build_actual_tool_used(contract, software),
        "status": "planned" if dry_run else "completed",
        "source_structure": structure_artifact["path"],
        "structure_artifact_id": structure_artifact["artifact_id"],
        "structure_manifest_artifact_id": structure_manifest_artifact["artifact_id"],
        "parent_artifact_ids": parent_artifact_ids,
        "generated_files": [],
        "missing_optional_inputs": [],
        "artifact_dir": ".simflow/artifacts/input_generation",
        "downstream_compute_hints": {
            "recommended_scheduler": params.get("scheduler", "slurm"),
            "software": software,
            "task": task,
        },
    }

    if dry_run:
        manifest["planned_outputs"] = [
            ".simflow/reports/input_generation/input_manifest.json",
            ".simflow/artifacts/input_generation",
        ]
        return {
            "status": "dry_run_complete",
            "manifest": manifest,
            "inputs": parent_artifact_ids,
            "planned_outputs": manifest["planned_outputs"],
        }

    artifacts_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    if software == "vasp":
        kppa = int((params or {}).get("kppa") or contract.get("parameter_overrides", {}).get("kppa") or 1000)
        generation = GENERATE_VASP_INPUTS(
            str(structure_path),
            task,
            str(artifacts_dir),
            params=stage_params,
            kppa=kppa,
            potcar_root=params.get("potcar_root"),
            use_vaspkit=bool(params.get("use_vaspkit", False)),
        )
        generated_files = [_relative_path(project_root, Path(path)) for path in generation["files_generated"]]
        manifest.update({
            "generated_files": generated_files,
            "missing_optional_inputs": [] if (artifacts_dir / "POTCAR").is_file() else ["POTCAR"],
            "num_atoms": generation["num_atoms"],
            "elements": generation["elements"],
            "kpoints_mesh": generation["kpoints_mesh"],
            "potcar": generation["potcar"],
        })
    elif software == "cp2k":
        cif_path = _materialize_cp2k_structure(structure_path, artifacts_dir / "structure.cif")
        generation = GENERATE_CP2K_INPUTS(str(cif_path), task, str(artifacts_dir), params=stage_params)
        generated_files = [_relative_path(project_root, cif_path)] + [
            _relative_path(project_root, Path(path)) for path in generation["files_generated"]
        ]
        manifest.update({
            "generated_files": generated_files,
            "num_atoms": generation["parameters"]["natoms"],
            "elements": generation["parameters"]["elements"],
            "cp2k_parameters": generation["parameters"],
        })
    elif software == "lammps":
        merged = _lammps_generation_params(contract, params)
        missing = _missing_lammps_generation_inputs(merged)
        if missing:
            return {
                "status": "error",
                "message": "Missing LAMMPS input-generation parameters: " + ", ".join(missing),
                "missing_inputs": missing,
            }
        generation = GENERATE_LAMMPS_INPUTS(
            str(structure_path),
            task,
            str(artifacts_dir),
            pair_style=str(merged.get("pair_style", "lj/cut")),
            pair_coeff=str(merged["pair_coeff"]),
            params=merged,
        )
        if generation.get("status") != "success":
            return generation
        generated_files = [
            _relative_path(project_root, Path(path)) for path in generation["files_generated"]
        ]
        manifest.update({
            "generated_files": generated_files,
            "num_atoms": generation["structure"]["num_atoms"],
            "elements": generation["structure"]["elements"],
            "lammps_manifest": generation["manifest"],
            "force_field_provenance": generation["manifest"]["force_field_provenance"],
            "warnings": generation.get("warnings", []),
        })
    elif software in {"gpumd", "nep"}:
        generation = GENERATE_GPUMD_INPUTS(
            str(structure_path) if software == "gpumd" else None,
            task,
            str(project_root),
            calc_dir=str(artifacts_dir.relative_to(project_root)),
            params=stage_params,
            software=software,
        )
        if generation.get("status") != "success":
            return generation
        generated_files = [
            _relative_path(project_root, Path(path)) for path in generation["files_generated"]
        ]
        manifest.update({
            "generated_files": generated_files,
            "num_atoms": generation.get("parameters", {}).get("num_atoms"),
            "elements": generation.get("parameters", {}).get("elements", []),
            "gpumd_nep_parameters": generation.get("parameters", {}),
            "warnings": generation.get("warnings", []),
        })
    else:
        return capability_warning(contract, "computation", "input_generation", software)

    manifest_path = reports_dir / "input_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    manifest_artifact = register_artifact(
        "input_manifest.json",
        "input_manifest",
        "computation",
        project_root=str(project_root),
        path=_relative_path(project_root, manifest_path),
        parent_artifacts=parent_artifact_ids,
        parameters={"software": software, "task": task},
        software=software,
        metadata={
            "actual_tool_used": manifest.get("actual_tool_used"),
            "execution_mode": "completed",
        },
    )
    file_artifacts = []
    for rel_path in manifest["generated_files"]:
        file_artifacts.append(register_artifact(
            Path(rel_path).name,
            "input_files",
            "computation",
            project_root=str(project_root),
            path=rel_path,
            parent_artifacts=[manifest_artifact["artifact_id"]],
            parameters={"software": software, "task": task},
            software=software,
            metadata={
                "actual_tool_used": manifest.get("actual_tool_used"),
                "execution_mode": "completed",
            },
        ))

    return {
        "status": "success",
        "artifacts": [manifest_artifact, *file_artifacts],
        "manifest": manifest,
        "inputs": parent_artifact_ids,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the canonical input generation stage")
    parser.add_argument("--workflow-dir", required=True, help="Path to .simflow directory")
    parser.add_argument("--params", type=str, default="{}", help="JSON parameters for the stage")
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--execute", dest="dry_run", action="store_false")
    args = parser.parse_args()

    try:
        params = json.loads(args.params)
        result = run_input_generation_stage(args.workflow_dir, params=params, dry_run=args.dry_run)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except Exception as exc:
        print(json.dumps({"status": "error", "message": str(exc)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
