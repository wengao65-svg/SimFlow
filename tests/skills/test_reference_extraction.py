"""Behavioral tests for the scientific reference-extraction Task Skill."""

from __future__ import annotations

import csv
import importlib.util
import io
import json
import subprocess
import sys
import tarfile
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
SKILL_DIR = ROOT / "skills" / "simflow-reference-extraction"
SCRIPT = SKILL_DIR / "scripts" / "extract_reference_data.py"
MODULE_PATH = SKILL_DIR / "scripts" / "_reference_extractor.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("simflow_reference_extractor", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _run(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=check,
    )


def test_skill_contract_and_progressive_references_are_present():
    text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    for section in [
        "## Purpose",
        "## Use when",
        "## Do not use when",
        "## Task principles",
        "## Minimum checks",
        "## Common failure modes",
        "## Escalate uncertainty when",
        "## Completion criteria",
        "## Optional references",
    ]:
        assert section in text
    for name in [
        "provenance.md",
        "source-extraction.md",
        "vector-extraction.md",
        "raster-extraction.md",
        "schema.md",
    ]:
        assert f"references/{name}" in text
        assert (SKILL_DIR / "references" / name).is_file()


def test_help_does_not_require_optional_scientific_packages():
    result = subprocess.run(
        [sys.executable, "-S", str(SCRIPT), "--help"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "source-extract" in result.stdout
    assert "raster-heatmap-extract" in result.stdout


def test_source_extract_preserves_a0_contract_without_runtime_state(tmp_path: Path):
    source = tmp_path / "reported.csv"
    source.write_text("pressure_GPa,value,error\n0,1.0,0.1\n5,1.5,0.2\n", encoding="utf-8")
    output = tmp_path / "normalized"

    result = _run(
        "source-extract",
        str(source),
        "--kind",
        "raw",
        "--out",
        str(output),
        "--quantity",
        "Reported value",
    )

    metadata = json.loads((output / "metadata.json").read_text(encoding="utf-8"))
    rows = list(csv.DictReader((output / "reference_data.csv").open(encoding="utf-8")))
    stdout = json.loads(result.stdout)
    assert metadata["schema_version"] == "0.3"
    assert metadata["extraction"]["provenance_grade"] == "A0"
    assert "helper_evidence" not in metadata
    assert stdout["helper_evidence"]["schema_version"] == "simflow.helper_evidence.v1"
    assert len(rows) == 2
    assert not (tmp_path / ".simflow").exists()


def test_nonempty_output_requires_explicit_overwrite(tmp_path: Path):
    source = tmp_path / "reported.csv"
    source.write_text("x,y\n0,1\n", encoding="utf-8")
    output = tmp_path / "normalized"
    output.mkdir()
    sentinel = output / "keep.txt"
    sentinel.write_text("existing evidence", encoding="utf-8")

    blocked = _run(
        "source-extract",
        str(source),
        "--kind",
        "raw",
        "--out",
        str(output),
        check=False,
    )
    assert blocked.returncode == 2
    assert "Pass --overwrite" in blocked.stderr
    assert sentinel.read_text(encoding="utf-8") == "existing evidence"

    _run(
        "source-extract",
        str(source),
        "--kind",
        "raw",
        "--out",
        str(output),
        "--overwrite",
    )
    assert not sentinel.exists()
    assert (output / "metadata.json").is_file()


def test_archive_manifest_is_ephemeral_and_rejects_path_traversal(tmp_path: Path):
    safe_archive = tmp_path / "source.tar.gz"
    with tarfile.open(safe_archive, "w:gz") as archive:
        payload = b"x,y\n0,1\n"
        info = tarfile.TarInfo("paper/data.csv")
        info.size = len(payload)
        archive.addfile(info, io.BytesIO(payload))
    output = tmp_path / "manifest"
    _run("source-manifest", str(safe_archive), "--out", str(output))
    manifest = json.loads((output / "source_manifest.json").read_text(encoding="utf-8"))
    assert manifest["archive_inspection_ephemeral"] is True
    assert manifest["source_root"] is None
    assert not (output / "source").exists()

    unsafe_archive = tmp_path / "unsafe.tar"
    with tarfile.open(unsafe_archive, "w") as archive:
        payload = b"bad"
        info = tarfile.TarInfo("../escape.txt")
        info.size = len(payload)
        archive.addfile(info, io.BytesIO(payload))
    blocked = _run(
        "source-manifest",
        str(unsafe_archive),
        "--out",
        str(tmp_path / "unsafe-output"),
        check=False,
    )
    assert blocked.returncode == 2
    assert "Unsafe archive path" in blocked.stderr
    assert not (tmp_path / "escape.txt").exists()


def test_dataset_validation_reports_missing_and_valid_outputs(tmp_path: Path):
    dataset = tmp_path / "dataset"
    dataset.mkdir()
    module = _load_module()
    missing = module.dataset_validate(dataset)
    assert missing["ok"] is False
    assert "metadata.json missing" in missing["issues"]

    (dataset / "reference_data.csv").write_text("x,y\n0,1\n", encoding="utf-8")
    (dataset / "metadata.json").write_text(
        json.dumps(
            {
                "schema_version": "0.3",
                "extraction": {"provenance_grade": "A2"},
                "outputs": {"csv": "reference_data.csv"},
            }
        ),
        encoding="utf-8",
    )
    valid = module.dataset_validate(dataset)
    assert valid["ok"] is True
    assert valid["row_count"] == 1


def test_raster_line_and_heatmap_paths_use_compact_synthetic_inputs(tmp_path: Path):
    np = pytest.importorskip("numpy")
    image_module = pytest.importorskip("PIL.Image")
    pytest.importorskip("cv2")

    rgb = np.full((120, 180, 3), 255, dtype=np.uint8)
    rgb[20:101, 20] = 0
    rgb[100, 20:161] = 0
    for x in range(25, 156):
        y = int(round(95 - 0.45 * (x - 25)))
        rgb[max(21, y - 1):min(99, y + 2), x] = [255, 0, 0]
    line_image = tmp_path / "line.png"
    image_module.fromarray(rgb).save(line_image)
    line_out = tmp_path / "line-output"
    _run(
        "raster-extract",
        str(line_image),
        "--out",
        str(line_out),
        "--plot-bbox",
        "20,20,160,100",
        "--mode",
        "line",
        "--series",
        "Series_A=#ff0000",
        "--x-min",
        "0",
        "--x-max",
        "10",
        "--y-min",
        "0",
        "--y-max",
        "5",
        "--quantity",
        "Synthetic line",
    )
    line_metadata = json.loads((line_out / "metadata.json").read_text(encoding="utf-8"))
    assert line_metadata["extraction"]["provenance_grade"] == "C1"
    assert (line_out / "raster_overlay.png").is_file()
    assert sum(1 for _ in csv.DictReader((line_out / "reference_data.csv").open())) > 50

    heatmap = np.zeros((80, 140, 3), dtype=np.uint8)
    gradient = np.linspace(0, 255, 60, dtype=np.uint8)
    for index, value in enumerate(gradient):
        color = [value, 0, 255 - value]
        heatmap[10:70, 10 + index] = color
        heatmap[10 + index, 100:110] = color
    heatmap_image = tmp_path / "heatmap.png"
    image_module.fromarray(heatmap).save(heatmap_image)
    heatmap_out = tmp_path / "heatmap-output"
    _run(
        "raster-heatmap-extract",
        str(heatmap_image),
        "--out",
        str(heatmap_out),
        "--heatmap-bbox",
        "10,10,69,69",
        "--colorbar-bbox",
        "100,10,109,69",
        "--colorbar-min",
        "0",
        "--colorbar-max",
        "1",
        "--colorbar-orientation",
        "vertical",
        "--colorbar-min-position",
        "top",
        "--x-min",
        "0",
        "--x-max",
        "1",
        "--y-min",
        "0",
        "--y-max",
        "1",
        "--stride",
        "4",
        "--quantity",
        "Synthetic field",
    )
    heatmap_metadata = json.loads((heatmap_out / "metadata.json").read_text(encoding="utf-8"))
    assert heatmap_metadata["quality"]["valid_fraction"] > 0.95
    assert (heatmap_out / "heatmap_reconstruction.png").is_file()
    assert (heatmap_out / "heatmap_color_error.png").is_file()


def test_vector_path_markers_and_errorbars_use_compact_synthetic_pdf(tmp_path: Path):
    fitz = pytest.importorskip("fitz")
    pdf = tmp_path / "vector.pdf"
    document = fitz.open()
    page = document.new_page(width=300, height=240)
    page.draw_rect(fitz.Rect(40, 30, 260, 200), color=(0, 0, 0), width=1)
    page.draw_polyline(
        [
            fitz.Point(50, 180),
            fitz.Point(100, 150),
            fitz.Point(150, 110),
            fitz.Point(200, 80),
            fitz.Point(250, 50),
        ],
        color=(1, 0, 0),
        width=1.5,
    )
    for x, y in [(60, 170), (110, 140), (160, 100), (210, 70)]:
        page.draw_circle(fitz.Point(x, y), 3, color=(0, 0, 1), fill=(0, 0, 1))
        page.draw_line(fitz.Point(x, y - 8), fitz.Point(x, y + 8), color=(0, 0, 1), width=1)
    document.save(pdf)
    document.close()

    path_output = tmp_path / "vector-path"
    _run(
        "vector-extract",
        str(pdf),
        "--out",
        str(path_output),
        "--axes-rect",
        "40,30,260,200",
        "--series",
        "1=Series_A",
        "--x-min",
        "0",
        "--x-max",
        "10",
        "--y-min",
        "0",
        "--y-max",
        "5",
        "--quantity",
        "Synthetic vector path",
    )
    path_metadata = json.loads((path_output / "metadata.json").read_text(encoding="utf-8"))
    path_rows = list(csv.DictReader((path_output / "reference_data.csv").open()))
    assert path_metadata["extraction"]["provenance_grade"] == "B2"
    assert len(path_rows) == 5
    assert (path_output / "vector_overlay.png").is_file()

    marker_output = tmp_path / "vector-markers"
    _run(
        "vector-marker-extract",
        str(pdf),
        "--out",
        str(marker_output),
        "--axes-rect",
        "40,30,260,200",
        "--groups",
        "0=Series_B",
        "--with-yerr",
        "--x-min",
        "0",
        "--x-max",
        "10",
        "--y-min",
        "0",
        "--y-max",
        "5",
        "--quantity",
        "Synthetic vector markers",
    )
    marker_metadata = json.loads((marker_output / "metadata.json").read_text(encoding="utf-8"))
    marker_rows = list(csv.DictReader((marker_output / "reference_data.csv").open()))
    assert marker_metadata["extraction"]["provenance_grade"] == "B1"
    assert len(marker_rows) == 4
    assert all(row["errorbar_drawing_index"] for row in marker_rows)
    assert all(float(row["yerr_plus"]) > 0 for row in marker_rows)
    assert (marker_output / "marker_overlay.png").is_file()
