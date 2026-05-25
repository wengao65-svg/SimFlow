"""Tests for the user-facing end-to-end research workflow script."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from runtime.simflow_core.artifacts import list_artifacts


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "skills" / "simflow" / "scripts" / "run_research_workflow.py"


def _research_text() -> str:
    return "\n".join([
        "goal: prepare a traceable Si workflow",
        "material: Si diamond",
        "software: vasp",
        "method: dft",
        'parameters: {"encut": 520, "kppa": 100, "structure_type": "diamond", "lattice_param": 5.43, "elements": ["Si"]}',
        "note: Use dry-run computation evidence and do not submit real jobs.",
    ])


def test_research_workflow_script_runs_literature_to_writing(tmp_path):
    result = subprocess.run(
        [
            "python",
            str(SCRIPT),
            "--project-root",
            str(tmp_path),
            "--text",
            _research_text(),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    summary = json.loads(result.stdout)

    assert summary["status"] == "success"
    assert summary["current_stage"] == "writing"
    assert summary["workflow_status"] == "completed"
    assert summary["target_stage"] == "writing"
    assert summary["stages_executed"] == 6
    assert summary["completed_stages"] == [
        "literature_review",
        "proposal",
        "modeling",
        "computation",
        "analysis_visualization",
        "writing",
    ]
    assert summary["artifact_summary"]["total"] >= 30
    assert summary["checkpoint_summary"]["count"] >= 1
    assert summary["computation"]["dry_run_status"] in {"pass", "warning"}
    assert summary["computation"]["hpc_submit_gate_status"] == "block"
    assert (tmp_path / ".simflow" / "reports" / "research_workflow_summary.json").is_file()
    assert (tmp_path / ".simflow" / "reports" / "handoff" / "final_handoff.md").is_file()

    artifact_names = {artifact["name"] for artifact in list_artifacts(project_root=str(tmp_path))}
    assert {"literature_matrix.json", "proposal.md", "structure_manifest.json", "compute_plan.json", "results.md"}.issubset(artifact_names)


def test_research_workflow_script_supports_plan_only_dry_run(tmp_path):
    result = subprocess.run(
        [
            "python",
            str(SCRIPT),
            "--project-root",
            str(tmp_path),
            "--text",
            _research_text(),
            "--target-stage",
            "proposal",
            "--dry-run",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    summary = json.loads(result.stdout)

    assert summary["status"] == "success"
    assert summary["dry_run"] is True
    assert summary["target_stage"] == "proposal"
    assert summary["stages_executed"] == 2
    assert summary["artifact_summary"]["total"] == 0
    assert summary["completed_stages"] == []
    assert (tmp_path / ".simflow" / "reports" / "research_workflow_summary.json").is_file()
