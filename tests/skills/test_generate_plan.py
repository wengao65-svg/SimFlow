#!/usr/bin/env python3
"""Tests for simflow-plan canonical state behavior."""

import json
import sys
import tempfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[2] / "skills" / "simflow-plan" / "scripts"
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(ROOT))

from runtime.lib.state import init_workflow, read_state, write_state
from generate_plan import generate_plan


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


def _write_metadata(tmpdir: str, **overrides):
    metadata = {
        "workflow_id": read_state(tmpdir, "workflow.json")["workflow_id"],
        "workflow_type": "dft",
        "entry_point": "literature",
        "current_stage": "literature",
        "research_goal": "Study Si surface reconstruction",
        "material": "Si(001)",
        "software": "vasp",
        "parameters": {"encut": 520, "kpoints": "4x4x1"},
        "stages": DFT_STAGES,
    }
    metadata.update(overrides)
    write_state(metadata, project_root=tmpdir, state_file="metadata.json")
    return metadata


def test_generate_plan_reads_canonical_state_from_simflow_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        init_workflow("dft", "literature", tmpdir)
        metadata = _write_metadata(tmpdir)

        result = generate_plan(str(Path(tmpdir) / ".simflow"))
        workflow_state = read_state(tmpdir, "workflow.json")
        plan_path = Path(tmpdir) / ".simflow" / "plans" / "workflow_plan.json"
        written_plan = json.loads(plan_path.read_text(encoding="utf-8"))

        assert result["status"] == "success"
        assert result["plan"]["workflow_id"] == metadata["workflow_id"]
        assert [stage["name"] for stage in result["plan"]["stages"]] == DFT_STAGES
        assert result["plan"]["stages"][0]["tasks"] == [
            "Search relevant papers",
            "Extract key parameters",
            "Identify reference data",
        ]
        assert workflow_state["plan"] == "plans/workflow_plan.json"
        assert plan_path.is_file()
        assert [stage["name"] for stage in written_plan["stages"]] == DFT_STAGES


def test_generate_plan_prefers_canonical_state_over_legacy_files():
    with tempfile.TemporaryDirectory() as tmpdir:
        init_workflow("dft", "literature", tmpdir)
        _write_metadata(tmpdir, research_goal="Canonical goal")
        legacy_root = Path(tmpdir) / ".simflow"
        (legacy_root / "metadata.json").write_text(
            json.dumps({"research_goal": "Legacy goal", "stages": ["legacy_stage"]}, indent=2),
            encoding="utf-8",
        )
        (legacy_root / "workflow_state.json").write_text(
            json.dumps({"stages": ["legacy_stage"]}, indent=2),
            encoding="utf-8",
        )

        result = generate_plan(str(legacy_root))

        assert result["status"] == "success"
        assert result["plan"]["research_goal"] == "Canonical goal"
        assert [stage["name"] for stage in result["plan"]["stages"]] == DFT_STAGES
        assert all(stage["name"] != "legacy_stage" for stage in result["plan"]["stages"])


def test_generate_plan_writes_optional_markdown_output():
    with tempfile.TemporaryDirectory() as tmpdir:
        init_workflow("dft", "literature", tmpdir)
        _write_metadata(
            tmpdir,
            expected_outputs=["Relaxed structure", "Band structure"],
            risks=["Surface reconstruction may need larger slab"],
            approval_points=["Review k-point convergence"],
        )
        output_path = Path(tmpdir) / ".simflow" / "plans" / "proposal.md"

        result = generate_plan(str(Path(tmpdir) / ".simflow"), str(output_path))
        content = output_path.read_text(encoding="utf-8")

        assert result["status"] == "success"
        assert result["plan"]["output_file"] == str(output_path)
        assert "Study Si surface reconstruction" in content
        assert "Relaxed structure" in content
        assert "Review k-point convergence" in content
