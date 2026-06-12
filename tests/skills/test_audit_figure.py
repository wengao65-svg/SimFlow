"""Tests for the audit_figure.py helper."""

from __future__ import annotations

import base64
import json
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
SCRIPT_DIR = ROOT / "skills" / "simflow-analysis-visualization" / "scripts"
SCRIPT = SCRIPT_DIR / "audit_figure.py"
sys.path.insert(0, str(SCRIPT_DIR))


ONE_PIXEL_PNG = (
    b"iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8"
    b"/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
)


def _write_png(path: Path) -> None:
    path.write_bytes(base64.b64decode(ONE_PIXEL_PNG))


def test_audit_figure_reports_valid_png(tmp_path):
    from audit_figure import audit_figure

    figure = tmp_path / "figure.png"
    output = tmp_path / "audit.json"
    _write_png(figure)

    result = audit_figure(str(figure), str(output))

    assert result["status"] in {"passed", "warning", "skipped_optional_dependency"}
    assert result["checks"]["exists"] is True
    assert result["checks"]["non_empty"] is True
    assert output.is_file()
    assert json.loads(output.read_text(encoding="utf-8"))["figure"] == str(figure.resolve())


def test_audit_figure_reports_missing_and_empty_files(tmp_path):
    from audit_figure import audit_figure

    missing = audit_figure(str(tmp_path / "missing.png"), str(tmp_path / "missing.json"))
    assert missing["status"] == "error"
    assert missing["checks"]["exists"] is False

    empty = tmp_path / "empty.png"
    empty.write_bytes(b"")
    result = audit_figure(str(empty), str(tmp_path / "empty.json"))
    assert result["status"] == "error"
    assert result["checks"]["exists"] is True
    assert result["checks"]["non_empty"] is False


def test_audit_figure_flags_near_blank_image(tmp_path):
    pytest.importorskip("PIL")
    from PIL import Image
    from audit_figure import audit_figure

    figure = tmp_path / "blank.png"
    Image.new("RGB", (20, 20), "white").save(figure)

    result = audit_figure(str(figure), str(tmp_path / "blank_audit.json"))

    assert result["status"] == "warning"
    assert result["checks"]["near_blank"] is True
    assert any("nearly uniform" in warning for warning in result["warnings"])


def test_audit_figure_helper_run_recording_args(tmp_path):
    figure = tmp_path / "figure.png"
    output = tmp_path / "audit.json"
    _write_png(figure)

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--figure",
            str(figure),
            "--output",
            str(output),
            "--project-root",
            str(tmp_path),
            "--record-helper-run",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert payload["helper_run_id"].startswith("helper_")
    assert payload["helper_run_manifest_artifact_id"].startswith("art_")
    assert output.is_file()
    assert (tmp_path / ".simflow" / "artifacts" / "analysis_visualization" / "audit_figure_helper_run.json").is_file()
