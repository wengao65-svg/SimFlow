"""Tests for optional helper-run artifact recording."""

import json
import tempfile
from pathlib import Path

from runtime.simflow_core.helpers import list_helper_runs, record_helper_run
from runtime.simflow_core.lineage import get_lineage
from runtime.simflow_core.state import init_workflow, read_state


def test_record_helper_run_tracks_self_written_analysis_script():
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        init_workflow("custom", "analysis_visualization", project_root=tmpdir)
        script_path = project_root / "analysis" / "parse_outputs.py"
        raw_path = project_root / "data" / "raw.out"
        table_path = project_root / "analysis" / "summary.csv"
        figure_path = project_root / "figures" / "energy.png"
        script_path.parent.mkdir(parents=True, exist_ok=True)
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        figure_path.parent.mkdir(parents=True, exist_ok=True)
        script_path.write_text("print('custom analysis')\n", encoding="utf-8")
        raw_path.write_text("energy -1.0\n", encoding="utf-8")
        table_path.write_text("step,energy\n0,-1.0\n", encoding="utf-8")
        figure_path.write_text("png placeholder\n", encoding="utf-8")

        result = record_helper_run(
            project_root=tmpdir,
            stage="analysis_visualization",
            run_name="custom python analysis",
            helper_name="self_written_python",
            command="python analysis/parse_outputs.py data/raw.out",
            script_path="analysis/parse_outputs.py",
            input_paths=["data/raw.out"],
            output_paths=["analysis/summary.csv", "figures/energy.png"],
            environment={"python": "3.13", "packages": ["pandas", "matplotlib"]},
            metadata={"claim": "demo energy summary"},
        )

        artifacts = read_state(project_root=tmpdir, state_file="artifacts.json")
        helper_runs = list_helper_runs(project_root=tmpdir, stage="analysis_visualization")
        manifest_path = project_root / result["manifest_artifact"]["path"]

        assert result["status"] == "success"
        assert result["manifest"]["helper_name"] == "self_written_python"
        assert result["manifest"]["script_path"] == "analysis/parse_outputs.py"
        assert result["manifest"]["input_paths"] == ["data/raw.out"]
        assert result["manifest"]["output_paths"] == ["analysis/summary.csv", "figures/energy.png"]
        assert manifest_path.is_file()
        assert json.loads(manifest_path.read_text(encoding="utf-8"))["command"].startswith("python")
        assert len(helper_runs) == 1
        assert helper_runs[0]["metadata"]["helper_optional"] is True
        assert {artifact["type"] for artifact in result["artifacts"]} == {
            "helper_script",
            "helper_input",
            "helper_output",
            "helper_run_manifest",
        }
        artifact_names = {artifact["name"] for artifact in artifacts}

        assert artifact_names >= {
            "parse_outputs.py",
            "raw.out",
            "summary.csv",
            "energy.png",
        }
        assert any(
            name.startswith("custom_python_analysis_helper_")
            and name.endswith("_helper_run.json")
            for name in artifact_names
        )


def test_helper_output_lineage_links_script_and_inputs():
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        init_workflow("custom", "analysis_visualization", project_root=tmpdir)
        (project_root / "script.py").write_text("print('ok')\n", encoding="utf-8")
        (project_root / "input.dat").write_text("input\n", encoding="utf-8")
        (project_root / "output.dat").write_text("output\n", encoding="utf-8")

        result = record_helper_run(
            project_root=tmpdir,
            stage="analysis_visualization",
            run_name="lineage check",
            script_path="script.py",
            input_paths=["input.dat"],
            output_paths=["output.dat"],
        )

        artifacts_by_type = {}
        for artifact in result["artifacts"]:
            artifacts_by_type.setdefault(artifact["type"], []).append(artifact)
        script_id = artifacts_by_type["helper_script"][0]["artifact_id"]
        input_id = artifacts_by_type["helper_input"][0]["artifact_id"]
        output_id = artifacts_by_type["helper_output"][0]["artifact_id"]
        manifest_id = artifacts_by_type["helper_run_manifest"][0]["artifact_id"]
        output_lineage = get_lineage(output_id, project_root=tmpdir)
        manifest_lineage = get_lineage(manifest_id, project_root=tmpdir)

        assert script_id in output_lineage["parent_artifacts"]
        assert input_id in output_lineage["parent_artifacts"]
        assert output_id in manifest_lineage["parent_artifacts"]


def test_repeated_helper_run_recordings_create_distinct_manifest_paths(tmp_path):
    init_workflow("custom", "analysis_visualization", project_root=str(tmp_path))
    (tmp_path / "script.py").write_text("print('ok')\n", encoding="utf-8")
    (tmp_path / "output.dat").write_text("output\n", encoding="utf-8")

    first = record_helper_run(
        project_root=str(tmp_path),
        stage="analysis_visualization",
        run_name="manifest uniqueness",
        script_path="script.py",
        output_paths=["output.dat"],
    )
    second = record_helper_run(
        project_root=str(tmp_path),
        stage="analysis_visualization",
        run_name="manifest uniqueness",
        script_path="script.py",
        output_paths=["output.dat"],
    )

    assert first["manifest_artifact"]["path"] != second["manifest_artifact"]["path"]
    assert (tmp_path / first["manifest_artifact"]["path"]).is_file()
    assert (tmp_path / second["manifest_artifact"]["path"]).is_file()
