#!/usr/bin/env python3
"""Tests for local environment detection privacy."""

from __future__ import annotations

import json
from pathlib import Path

from runtime.simflow_core.environment import detect_potcar_library


def test_detect_potcar_library_reports_availability_without_private_paths(monkeypatch, tmp_path):
    private_potcar_root = tmp_path / "licensed" / "private" / "potpaw"
    private_vaspkit = "/private/tools/vaspkit/bin/vaspkit"
    potcar_dir = private_potcar_root / "PBE" / "Si"
    potcar_dir.mkdir(parents=True)
    (potcar_dir / "POTCAR").write_text("licensed content fixture\n", encoding="utf-8")
    monkeypatch.setenv("SIMFLOW_VASP_POTCAR_PATH", str(private_potcar_root))
    monkeypatch.setenv("SIMFLOW_VASP_POTCAR_FLAVOR", "PBE")
    monkeypatch.setattr("shutil.which", lambda name: private_vaspkit if name == "vaspkit" else None)

    result = detect_potcar_library()
    serialized = json.dumps(result)

    assert result["path_configured"] is True
    assert result["path_exists"] is True
    assert result["flavor"] == "PBE"
    assert result["element_count"] == 1
    assert result["vaspkit_available"] is True
    assert result["vaspkit_executable"] == Path(private_vaspkit).name
    assert "potcar_path" not in result
    assert "vaspkit_path" not in result
    assert str(private_potcar_root) not in serialized
    assert private_vaspkit not in serialized
