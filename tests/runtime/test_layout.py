"""Tests for advisory existing-layout-first placement."""

from runtime.simflow_core.layout import inspect_layout, recommend_analysis_location


def _write(root, relative):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("data\n", encoding="utf-8")
    return path


def test_layout_inspection_is_advisory_and_does_not_reorganize(tmp_path):
    (tmp_path / "stage0_legacy").mkdir()
    nested = tmp_path / "legacy_run" / ".simflow"
    nested.mkdir(parents=True)
    before = sorted(str(path.relative_to(tmp_path)) for path in tmp_path.rglob("*"))

    result = inspect_layout(str(tmp_path))

    assert result["enforcement"] == "advisory"
    assert result["requires_migration"] is False
    assert result["bare_stage_directories"] == ["stage0_legacy"]
    assert result["nested_simflow_directories"] == ["legacy_run/.simflow"]
    assert sorted(str(path.relative_to(tmp_path)) for path in tmp_path.rglob("*")) == before


def test_single_calculation_analysis_stays_with_its_input_unit(tmp_path):
    _write(tmp_path, "custom_project/md_300k/outputs/trajectory.xyz")
    result = recommend_analysis_location(
        str(tmp_path),
        ["custom_project/md_300k/outputs/trajectory.xyz"],
        topic="rdf",
    )
    assert result["scope"] == "calculation_unit"
    assert result["authoritative_location"] == "custom_project/md_300k/analysis/rdf"


def test_multiple_runs_in_one_stage_use_stage_analysis_entry(tmp_path):
    _write(tmp_path, "phase4_computation/stage1_force_field_validation/runs/La/output/thermo.out")
    _write(tmp_path, "phase4_computation/stage1_force_field_validation/runs/Lu/output/thermo.out")
    result = recommend_analysis_location(
        str(tmp_path),
        [
            "phase4_computation/stage1_force_field_validation/runs/La/output/thermo.out",
            "phase4_computation/stage1_force_field_validation/runs/Lu/output/thermo.out",
        ],
        topic="force_field_comparison",
    )
    assert result["scope"] == "stage"
    assert result["authoritative_location"] == (
        "phase4_computation/stage1_force_field_validation/analysis/force_field_comparison"
    )
    assert result["analysis_entry"] == "phase4_computation/stage1_force_field_validation/analysis/README.md"


def test_multiple_stages_in_one_phase_use_phase_analysis_entry(tmp_path):
    _write(tmp_path, "phase4_computation/stage1_relax/run/output.dat")
    _write(tmp_path, "phase4_computation/stage2_static/run/output.dat")
    result = recommend_analysis_location(
        str(tmp_path),
        [
            "phase4_computation/stage1_relax/run/output.dat",
            "phase4_computation/stage2_static/run/output.dat",
        ],
        topic="method_comparison",
    )
    assert result["scope"] == "phase"
    assert result["authoritative_location"] == "phase4_computation/analysis/method_comparison"


def test_phase5_is_used_only_for_explicit_project_level_analysis(tmp_path):
    _write(tmp_path, "phase3_modeling/stage1_structure/model.cif")
    _write(tmp_path, "phase4_computation/stage1_static/output.dat")
    inputs = [
        "phase3_modeling/stage1_structure/model.cif",
        "phase4_computation/stage1_static/output.dat",
    ]
    local = recommend_analysis_location(str(tmp_path), inputs, topic="consistency")
    project = recommend_analysis_location(
        str(tmp_path), inputs, topic="paper_summary", project_level=True
    )
    assert local["authoritative_location"] == "analysis/consistency"
    assert project["authoritative_location"] == "phase5_analysis_visualization/paper_summary"


def test_existing_results_name_is_respected_and_navigation_never_copies(tmp_path):
    _write(tmp_path, "workflows/validation/run1/output.dat")
    (tmp_path / "workflows" / "validation" / "results").mkdir()
    (tmp_path / "README.md").write_text("project\n", encoding="utf-8")
    result = recommend_analysis_location(
        str(tmp_path), ["workflows/validation/run1/output.dat"], topic="summary"
    )
    assert result["authoritative_location"] == "workflows/validation/results/summary"
    assert result["project_index"] == "README.md"
    assert result["actions"]["copy_results"] is False
    assert result["actions"]["create_symlink"] is False
