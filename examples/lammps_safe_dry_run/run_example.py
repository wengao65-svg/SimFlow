#!/usr/bin/env python3
"""Create a redistributable LAMMPS dry-run evidence package.

The example writes all generated state under the user-provided project root.
It never runs LAMMPS and never submits a local, remote, or HPC job.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from runtime.simflow_core.artifacts import list_artifacts, register_artifact
from runtime.simflow_core.checkpoints import create_checkpoint
from runtime.simflow_core.gates import check_gate
from runtime.simflow_core.readiness import build_stage_readiness
from runtime.simflow_core.state import ensure_workflow_initialized, update_stage, write_report


EXAMPLE_ROOT = Path(__file__).resolve().parent
INPUT_ROOT = EXAMPLE_ROOT / "input"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def _copy_inputs(project_root: Path) -> dict[str, Path]:
    target = project_root / ".simflow" / "artifacts" / "compute" / "lammps_safe"
    target.mkdir(parents=True, exist_ok=True)
    copied = {}
    for name in ("in.lammps", "data.lammps"):
        source = INPUT_ROOT / name
        destination = target / name
        shutil.copyfile(source, destination)
        copied[name] = destination
    return copied


def run_lammps_safe_example(project_root: Path) -> dict:
    project_root = project_root.expanduser().resolve()
    project_root.mkdir(parents=True, exist_ok=True)

    workflow = ensure_workflow_initialized(
        workflow_type="classical_md",
        entry_point="computation",
        project_root=str(project_root),
    )
    copied = _copy_inputs(project_root)
    now = datetime.now(timezone.utc).isoformat()
    relative_inputs = {
        name: str(path.relative_to(project_root))
        for name, path in copied.items()
    }
    input_hashes = {
        name: _sha256(path)
        for name, path in copied.items()
    }
    script_hash = input_hashes["in.lammps"]

    compute_dir = project_root / ".simflow" / "artifacts" / "compute"
    security_dir = project_root / ".simflow" / "artifacts" / "security"

    manifest = {
        "kind": "calculation_manifest",
        "software": "lammps",
        "recipe": "classical_md",
        "stage": "computation",
        "execution_mode": "dry_run_only",
        "command": "lmp -in in.lammps",
        "real_submit": False,
        "input_files": relative_inputs,
        "input_hashes": input_hashes,
        "script_hash": script_hash,
        "force_field": {
            "pair_style": "lj/cut",
            "pair_coeff": "1 1 1.0 1.0 2.5",
            "source": "synthetic redistributable fixture",
            "redistributed_by_simflow": True,
        },
        "created_at": now,
    }
    input_validation = {
        "kind": "input_validation_report",
        "software": "lammps",
        "status": "pass",
        "checked_files": list(relative_inputs.values()),
        "missing_required_files": [],
        "warnings": [
            {
                "code": "synthetic_fixture",
                "message": "This example is a dry-run fixture and is not a scientific production calculation.",
            }
        ],
        "created_at": now,
    }
    resource_estimate = {
        "kind": "resource_estimate",
        "software": "lammps",
        "status": "pass",
        "mode": "dry_run_only",
        "estimated_cores": 1,
        "estimated_walltime_minutes": 1,
        "estimated_storage_mb": 1,
        "created_at": now,
    }
    dry_run_report = {
        "kind": "dry_run_report",
        "software": "lammps",
        "status": "pass",
        "real_submit": False,
        "command_documented": True,
        "script_hash": script_hash,
        "input_hashes": input_hashes,
        "message": "LAMMPS input package prepared for dry-run evidence only; no job was executed.",
        "created_at": now,
    }
    credential_scan = {
        "kind": "credential_scan",
        "status": "pass",
        "scanned_paths": list(relative_inputs.values()),
        "findings": [],
        "created_at": now,
    }

    evidence_files = {
        "calculation_manifest": (compute_dir / "calculation_manifest.json", manifest),
        "input_validation_report": (compute_dir / "input_validation.json", input_validation),
        "resource_estimate": (compute_dir / "resource_estimate.json", resource_estimate),
        "dry_run_report": (compute_dir / "dry_run_report.json", dry_run_report),
        "credential_scan": (security_dir / "credential_scan.json", credential_scan),
    }
    for _, (path, payload) in evidence_files.items():
        _write_json(path, payload)

    input_artifacts = []
    for name, path in copied.items():
        artifact = register_artifact(
            name=f"lammps_safe_{name}",
            artifact_type="input_file",
            stage="computation",
            path=str(path.relative_to(project_root)),
            software="lammps",
            metadata={
                "evidence_keys": ["input_files"],
                "synthetic_fixture": True,
                "real_submit": False,
            },
            project_root=str(project_root),
        )
        input_artifacts.append(artifact["artifact_id"])

    parent_artifacts = list(input_artifacts)
    for evidence_key, (path, payload) in evidence_files.items():
        register_artifact(
            name=f"lammps_safe_{evidence_key}",
            artifact_type=evidence_key,
            stage="computation",
            path=str(path.relative_to(project_root)),
            parent_artifacts=parent_artifacts if evidence_key != "credential_scan" else [],
            software="lammps",
            metadata={
                "evidence_key": evidence_key,
                "evidence_keys": [evidence_key],
                "status": payload.get("status"),
                "real_submit": False,
            },
            project_root=str(project_root),
        )

    update_stage(
        "computation",
        "completed",
        project_root=str(project_root),
        outputs=[str(path.relative_to(project_root)) for path in copied.values()],
    )
    checkpoint = create_checkpoint(
        workflow_id=workflow["workflow_id"],
        stage_id="computation",
        description="LAMMPS safe dry-run evidence package created without executing a job.",
        project_root=str(project_root),
    )
    gate = check_gate("hpc_submit", {"project_root": str(project_root)})
    readiness = build_stage_readiness(str(project_root), stage="computation")

    summary = {
        "status": "success",
        "project_root": str(project_root),
        "workflow_id": workflow["workflow_id"],
        "current_stage": "computation",
        "software": "lammps",
        "real_submit": False,
        "artifact_count": len(list_artifacts(project_root=str(project_root))),
        "checkpoint_id": checkpoint["checkpoint_id"],
        "computation_readiness": readiness["readiness_status"],
        "hpc_submit_gate_status": gate["status"],
        "important_paths": {
            "calculation_manifest": ".simflow/artifacts/compute/calculation_manifest.json",
            "input_validation": ".simflow/artifacts/compute/input_validation.json",
            "resource_estimate": ".simflow/artifacts/compute/resource_estimate.json",
            "dry_run_report": ".simflow/artifacts/compute/dry_run_report.json",
            "credential_scan": ".simflow/artifacts/security/credential_scan.json",
        },
    }
    _write_json(project_root / ".simflow" / "reports" / "lammps_safe_example_summary.json", summary)
    write_report(
        "\n".join([
            "# LAMMPS Safe Dry-Run Handoff",
            "",
            "- Software: LAMMPS",
            "- Execution: dry-run evidence only",
            "- Real submit: false",
            f"- Submit gate status: {gate['status']}",
            f"- Checkpoint: {checkpoint['checkpoint_id']}",
            "",
        ]),
        project_root=str(project_root),
        report_file="handoff/lammps_safe_handoff.md",
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the SimFlow LAMMPS safe dry-run example")
    parser.add_argument("--project-root", required=True, help="Disposable project directory for generated .simflow state")
    args = parser.parse_args()

    result = run_lammps_safe_example(Path(args.project_root))
    print(json.dumps(result, indent=2, ensure_ascii=False))
    if result.get("status") != "success":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
