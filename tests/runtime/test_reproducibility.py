#!/usr/bin/env python3
"""Tests for runtime/lib/reproducibility.py."""

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from runtime.lib.artifact import register_artifact
from runtime.lib.checkpoint import create_checkpoint
from runtime.lib.reproducibility import build_reproducibility_manifest
from runtime.lib.state import init_workflow, read_state, write_state

DFT_STAGES = [
    "literature",
    "review",
    "proposal",
    "modeling",
    "input_generation",
    "compute",
    "analysis",
    "visualization",
    "writing",
]


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _seed_reproducibility_state(tmpdir: str) -> Path:
    project_root = Path(tmpdir)
    init_workflow("dft", "literature", tmpdir)
    workflow = read_state(tmpdir, "workflow.json")
    workflow.update({
        "current_stage": "visualization",
        "status": "in_progress",
        "plan": ".simflow/plans/workflow_plan.json",
    })
    write_state(workflow, project_root=tmpdir, state_file="workflow.json")
    write_state(
        {
            "workflow_id": workflow["workflow_id"],
            "workflow_type": "dft",
            "entry_point": "literature",
            "current_stage": "visualization",
            "stages": DFT_STAGES,
            "research_goal": "Study Si surface reconstruction",
            "material": "Si(001)",
            "software": "vasp",
        },
        project_root=tmpdir,
        state_file="metadata.json",
    )
    write_state(
        {
            stage: {
                "stage_name": stage,
                "status": "completed" if stage != "writing" else "pending",
                "agent": None,
                "inputs": [],
                "outputs": [],
                "checkpoint_id": None,
                "error_message": None,
                "started_at": "2026-01-01T00:00:00+00:00",
                "completed_at": None if stage == "writing" else "2026-01-01T00:10:00+00:00",
            }
            for stage in DFT_STAGES
        },
        project_root=tmpdir,
        state_file="stages.json",
    )

    proposal_path = project_root / ".simflow" / "plans" / "proposal.md"
    structure_manifest_path = project_root / ".simflow" / "reports" / "modeling" / "structure_manifest.json"
    compute_plan_path = project_root / ".simflow" / "reports" / "compute" / "compute_plan.json"
    analysis_report_path = project_root / ".simflow" / "reports" / "analysis" / "analysis_report.json"
    figures_manifest_path = project_root / ".simflow" / "reports" / "visualization" / "figures_manifest.json"
    figure_path = project_root / ".simflow" / "artifacts" / "visualization" / "energy_convergence.png"
    methods_path = project_root / ".simflow" / "reports" / "writing" / "methods.md"
    results_path = project_root / ".simflow" / "reports" / "writing" / "results.md"

    proposal_path.parent.mkdir(parents=True, exist_ok=True)
    proposal_path.write_text("# Proposal\n", encoding="utf-8")
    _write_json(
        structure_manifest_path,
        {
            "source_mode": "prototype",
            "structure_files": ["structures/si001.cif"],
            "validation": {"status": "ok"},
        },
    )
    _write_json(
        compute_plan_path,
        {
            "software": "vasp",
            "task": "relax",
            "dry_run": True,
            "real_submit": False,
            "approval_required_for_real_submit": True,
            "recommended_command": "vasp_std > vasp.out",
            "gate_status": {"name": "hpc_submit", "approved": False},
        },
    )
    _write_json(
        analysis_report_path,
        {
            "status": "waiting_for_outputs",
            "software": "vasp",
            "task": "relax",
            "conclusions": "Awaiting real outputs.",
        },
    )
    _write_json(
        figures_manifest_path,
        {
            "status": "waiting_for_outputs",
            "figures": [
                {
                    "name": "energy_convergence.png",
                    "path": ".simflow/artifacts/visualization/energy_convergence.png",
                    "title": "Energy Convergence",
                }
            ],
            "skipped_reasons": [],
        },
    )
    figure_path.parent.mkdir(parents=True, exist_ok=True)
    figure_path.write_bytes(b"png")
    methods_path.parent.mkdir(parents=True, exist_ok=True)
    methods_path.write_text("# Methods\n", encoding="utf-8")
    results_path.write_text("# Results\n", encoding="utf-8")

    proposal_artifact = register_artifact(
        "proposal.md",
        "proposal",
        "proposal",
        project_root=tmpdir,
        path=".simflow/plans/proposal.md",
    )
    structure_artifact = register_artifact(
        "structure_manifest.json",
        "structure_manifest",
        "modeling",
        project_root=tmpdir,
        path=".simflow/reports/modeling/structure_manifest.json",
        parent_artifacts=[proposal_artifact["artifact_id"]],
        parameters={"source_structure": str(project_root / "inputs" / "Si001.cif")},
        software="vasp",
    )
    compute_artifact = register_artifact(
        "compute_plan.json",
        "compute_plan",
        "compute",
        project_root=tmpdir,
        path=".simflow/reports/compute/compute_plan.json",
        parent_artifacts=[structure_artifact["artifact_id"]],
        parameters={"scheduler": "slurm"},
        software="vasp",
    )
    analysis_artifact = register_artifact(
        "analysis_report.json",
        "analysis_report",
        "analysis",
        project_root=tmpdir,
        path=".simflow/reports/analysis/analysis_report.json",
        parent_artifacts=[compute_artifact["artifact_id"]],
        parameters={"source_file": str(project_root / "outputs" / "OUTCAR")},
        software="vasp",
    )
    figures_manifest_artifact = register_artifact(
        "figures_manifest.json",
        "figures_manifest",
        "visualization",
        project_root=tmpdir,
        path=".simflow/reports/visualization/figures_manifest.json",
        parent_artifacts=[analysis_artifact["artifact_id"]],
        parameters={"status": "waiting_for_outputs"},
        software="vasp",
    )
    register_artifact(
        "energy_convergence.png",
        "figure",
        "visualization",
        project_root=tmpdir,
        path=".simflow/artifacts/visualization/energy_convergence.png",
        parent_artifacts=[figures_manifest_artifact["artifact_id"]],
        software="vasp",
    )
    register_artifact(
        "methods.md",
        "methods",
        "writing",
        project_root=tmpdir,
        path=".simflow/reports/writing/methods.md",
        parent_artifacts=[proposal_artifact["artifact_id"], structure_artifact["artifact_id"]],
        software="vasp",
    )
    register_artifact(
        "results.md",
        "results",
        "writing",
        project_root=tmpdir,
        path=".simflow/reports/writing/results.md",
        parent_artifacts=[analysis_artifact["artifact_id"], figures_manifest_artifact["artifact_id"]],
        software="vasp",
    )

    create_checkpoint(workflow["workflow_id"], "compute", "Compute dry run complete", project_root=tmpdir)
    create_checkpoint(workflow["workflow_id"], "visualization", "Visualization manifest recorded", project_root=tmpdir)
    return project_root


def test_build_reproducibility_manifest_from_canonical_registries():
    with tempfile.TemporaryDirectory() as tmpdir:
        _seed_reproducibility_state(tmpdir)

        manifest = build_reproducibility_manifest(
            project_root=tmpdir,
            planned_outputs={
                "reproducibility_package": ".simflow/reports/reproducibility/reproducibility_package.md",
                "reproducibility_manifest": ".simflow/reports/reproducibility/reproducibility_manifest.json",
            },
        )

        dumped = json.dumps(manifest, ensure_ascii=False)

        assert manifest["workflow_metadata"]["workflow_type"] == "dft"
        assert manifest["workflow_metadata"]["current_stage"] == "visualization"
        assert manifest["completed_stages"] == DFT_STAGES[:-1]
        assert manifest["pending_stages"] == ["writing"]
        assert any(artifact["name"] == "compute_plan.json" for artifact in manifest["artifact_index"])
        assert any(artifact["lineage"]["parent_artifacts"] for artifact in manifest["artifact_index"])
        assert manifest["checkpoint_summary"]["count"] == 2
        assert manifest["checkpoint_summary"]["latest"]["stage_id"] == "visualization"
        assert manifest["execution_truth"]["dry_run"] is True
        assert manifest["execution_truth"]["real_submit"] is False
        assert manifest["execution_truth"]["approval_required"] is True
        assert manifest["execution_truth"]["approval_required_for_real_submit"] is True
        assert manifest["figure_provenance"]["figure_count"] == 1
        assert manifest["writing_artifact_references"]["methods"]["name"] == "methods.md"
        assert manifest["writing_artifact_references"]["results"]["name"] == "results.md"
        assert manifest["writing_artifact_references"]["planned_outputs"]["reproducibility_package"].endswith("reproducibility_package.md")
        assert tmpdir not in dumped
        assert any(warning["type"] == "sanitized_path" for warning in manifest["warnings"])
