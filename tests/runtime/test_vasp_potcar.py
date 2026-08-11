#!/usr/bin/env python3
"""Tests for restricted VASP POTCAR materialization and metadata."""

from __future__ import annotations

import json
import os
import stat
import sys
from pathlib import Path

import pytest

from runtime.simflow_helpers.engines.vasp_potcar import (
    _extract_potcar_datasets,
    _extract_potcar_elements,
    _find_element_potcar,
    _list_available_elements,
    generate_potcar,
    get_potcar_flavor,
    get_potcar_path,
    read_poscar_species,
    resolve_potcar_setups,
    validate_potcar,
)


def _write_poscar(path: Path, species: str, counts: str) -> Path:
    path.write_text(
        f"Test\n1.0\n5 0 0\n0 5 0\n0 0 5\n{species}\n{counts}\nDirect\n0 0 0\n",
        encoding="utf-8",
    )
    return path


def _potcar_text(dataset: str, zval: float = 4.0, marker: str = "") -> str:
    return (
        f"PAW_PBE {dataset} 05Jan2001\n"
        f"POMASS = 1.0; ZVAL = {zval}\n"
        f"End of Dataset {marker}\n"
    )


def _create_library(root: Path, datasets: dict[str, str], *, nested: bool = True) -> Path:
    base = root / "PBE" if nested else root
    for dataset, content in datasets.items():
        target = base / dataset
        target.mkdir(parents=True, exist_ok=True)
        (target / "POTCAR").write_text(content, encoding="utf-8")
    return root


class TestReadPoscarSpecies:
    def test_single_and_multiple_elements(self, tmp_path):
        assert read_poscar_species(str(_write_poscar(tmp_path / "POSCAR", "Si", "2"))) == ["Si"]
        assert read_poscar_species(str(_write_poscar(tmp_path / "POSCAR2", "Si Ge O", "2 2 4"))) == ["Si", "Ge", "O"]

    def test_vasp4_format_raises(self, tmp_path):
        poscar = tmp_path / "POSCAR"
        poscar.write_text("Test\n1.0\n5 0 0\n0 5 0\n0 0 5\n2 2\n4\nDirect\n0 0 0\n", encoding="utf-8")
        with pytest.raises(ValueError, match="VASP4"):
            read_poscar_species(str(poscar))

    def test_missing_and_short_files_raise(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            read_poscar_species(str(tmp_path / "missing"))
        short = tmp_path / "short"
        short.write_text("one\ntwo\n", encoding="utf-8")
        with pytest.raises(ValueError, match="too short"):
            read_poscar_species(str(short))


class TestSetupResolver:
    @pytest.mark.parametrize(
        ("setups", "expected"),
        [
            (None, ["Fe", "O"]),
            ("minimal", ["Fe", "O"]),
            ("recommended", ["Li_sv", "O"]),
            ("gw", ["Fe_sv_GW", "O_GW"]),
            ({"base": "recommended", "Fe": "_pv", "O": ""}, ["Fe_pv", "O"]),
        ],
    )
    def test_fixed_profiles_and_overrides(self, setups, expected):
        elements = ["Li", "O"] if setups == "recommended" else ["Fe", "O"]
        result = resolve_potcar_setups(elements, setups)
        assert result["status"] == "success"
        assert result["resolved_datasets"] == expected
        assert result["ase_version"]
        assert result["content_included"] is False

    @pytest.mark.parametrize("profile", ["materialsproject", "future-profile", ""])
    def test_unknown_profiles_are_stably_rejected(self, profile):
        result = resolve_potcar_setups(["Fe"], profile)
        assert result["status"] == "error"
        assert result["reason_code"] == "unsupported_potcar_setup_profile"
        assert result["supported_profiles"] == ["minimal", "recommended", "gw"]

    def test_atom_index_and_unknown_element_overrides_are_rejected(self):
        indexed = resolve_potcar_setups(["Fe"], {"base": "minimal", 0: "Fe_pv"})
        unknown = resolve_potcar_setups(["Fe"], {"base": "minimal", "Co": "_pv"})
        assert indexed["reason_code"] == "atom_index_setup_unsupported"
        assert unknown["reason_code"] == "potcar_setup_unknown_element"

    def test_missing_ase_only_blocks_setup_resolution(self, monkeypatch):
        monkeypatch.setitem(sys.modules, "ase", None)
        result = resolve_potcar_setups(["Si"], None)
        assert result["reason_code"] == "potcar_setup_dependency_missing"

    def test_unknown_profile_is_rejected_before_ase_import(self, monkeypatch):
        monkeypatch.setitem(sys.modules, "ase", None)
        result = resolve_potcar_setups(["Si"], "future-profile")
        assert result["reason_code"] == "unsupported_potcar_setup_profile"


class TestDatasetInspection:
    def test_extracts_full_dataset_labels_and_base_elements(self, tmp_path):
        potcar = tmp_path / "POTCAR"
        potcar.write_text(_potcar_text("Fe_pv") + _potcar_text("O"), encoding="utf-8")
        assert _extract_potcar_datasets(potcar) == ["Fe_pv", "O"]
        assert _extract_potcar_elements(str(potcar)) == ["Fe", "O"]

    def test_find_is_exact_and_never_uses_wildcard_fallback(self, tmp_path):
        _create_library(tmp_path, {"Fe_pv": _potcar_text("Fe_pv")})
        assert _find_element_potcar(str(tmp_path), "PBE", "Fe") is None
        selected = _find_element_potcar(str(tmp_path), "PBE", "Fe", dataset="Fe_pv")
        assert selected is not None
        assert selected.parent.name == "Fe_pv"

    def test_lists_dataset_directories_for_nested_and_direct_roots(self, tmp_path):
        nested = tmp_path / "nested"
        direct = tmp_path / "direct"
        _create_library(nested, {"Si": _potcar_text("Si"), "Fe_pv": _potcar_text("Fe_pv")})
        _create_library(direct, {"O": _potcar_text("O")}, nested=False)
        assert _list_available_elements(str(nested), "PBE") == ["Fe_pv", "Si"]
        assert _list_available_elements(str(direct), "PBE") == ["O"]


class TestGeneratePotcar:
    def test_materializes_exact_datasets_in_poscar_order_without_returning_content(self, tmp_path):
        library = _create_library(
            tmp_path / "licensed" / "private",
            {
                "Fe_pv": _potcar_text("Fe_pv", 8.0, "PRIVATE_FE_MARKER"),
                "O": _potcar_text("O", 6.0, "PRIVATE_O_MARKER"),
            },
        )
        calc = tmp_path / "phase4_computation" / "stage1_vasp" / "run_step1"
        calc.mkdir(parents=True)
        poscar = _write_poscar(calc / "POSCAR", "Fe O", "1 1")
        output = calc / "POTCAR"

        result = generate_potcar(
            str(poscar),
            str(output),
            potcar_root=str(library),
            setups={"base": "minimal", "Fe": "_pv"},
            project_root=str(tmp_path),
        )

        assert result["status"] == "materialized"
        assert result["resolved_datasets"] == ["Fe_pv", "O"]
        assert result["validation"]["valid"] is True
        assert result["sha256"]
        assert result["size_bytes"] == output.stat().st_size
        assert stat.S_IMODE(output.stat().st_mode) == 0o600
        assert _extract_potcar_datasets(output) == ["Fe_pv", "O"]
        serialized = json.dumps(result)
        assert str(library) not in serialized
        assert "PRIVATE_FE_MARKER" not in serialized
        assert "PRIVATE_O_MARKER" not in serialized

    def test_supports_direct_dataset_root(self, tmp_path):
        library = _create_library(tmp_path / "potpaw_PBE", {"Si": _potcar_text("Si")}, nested=False)
        calc = tmp_path / "calc"
        calc.mkdir()
        poscar = _write_poscar(calc / "POSCAR", "Si", "2")
        result = generate_potcar(str(poscar), str(calc / "POTCAR"), potcar_root=str(library))
        assert result["status"] == "materialized"
        assert result["resolved_datasets"] == ["Si"]

    def test_missing_exact_dataset_reports_candidates_without_fallback(self, tmp_path):
        library = _create_library(
            tmp_path / "potlib",
            {"Fe_pv": _potcar_text("Fe_pv"), "Fe_sv": _potcar_text("Fe_sv")},
        )
        calc = tmp_path / "calc"
        calc.mkdir()
        poscar = _write_poscar(calc / "POSCAR", "Fe", "1")
        output = calc / "POTCAR"
        result = generate_potcar(str(poscar), str(output), potcar_root=str(library), setups="minimal")
        assert result["status"] == "needs_inputs"
        assert result["reason_code"] == "potcar_dataset_missing"
        assert result["available_datasets"] == {"Fe": ["Fe_pv", "Fe_sv"]}
        assert not output.exists()

    def test_existing_dataset_sequence_mismatch_is_not_overwritten(self, tmp_path):
        library = _create_library(tmp_path / "potlib", {"Fe": _potcar_text("Fe")})
        calc = tmp_path / "calc"
        calc.mkdir()
        poscar = _write_poscar(calc / "POSCAR", "Fe", "1")
        output = calc / "POTCAR"
        original = _potcar_text("Fe_pv", marker="KEEP_EXISTING")
        output.write_text(original, encoding="utf-8")

        result = generate_potcar(str(poscar), str(output), potcar_root=str(library), setups="minimal")

        assert result["status"] == "error"
        assert result["reason_code"] == "existing_potcar_dataset_mismatch"
        assert output.read_text(encoding="utf-8") == original

    def test_existing_user_potcar_matches_resolved_minimal_without_library(self, tmp_path, monkeypatch):
        calc = tmp_path / "calc"
        calc.mkdir()
        poscar = _write_poscar(calc / "POSCAR", "Si", "2")
        output = calc / "POTCAR"
        output.write_text(_potcar_text("Si"), encoding="utf-8")
        monkeypatch.delenv("SIMFLOW_VASP_POTCAR_PATH", raising=False)
        result = generate_potcar(str(poscar), str(output))
        assert result["status"] == "existing"
        assert result["resolved_datasets"] == ["Si"]
        assert result["validation"]["valid"] is True

    def test_existing_potcar_reports_setup_dependency_error_when_ase_is_missing(self, tmp_path, monkeypatch):
        calc = tmp_path / "calc"
        calc.mkdir()
        poscar = _write_poscar(calc / "POSCAR", "Si", "2")
        output = calc / "POTCAR"
        output.write_text(_potcar_text("Si"), encoding="utf-8")
        monkeypatch.delenv("SIMFLOW_VASP_POTCAR_PATH", raising=False)
        monkeypatch.setitem(sys.modules, "ase", None)
        result = generate_potcar(str(poscar), str(output))
        assert result["reason_code"] == "potcar_setup_dependency_missing"

        basic_validation = validate_potcar(str(poscar), str(output))
        assert basic_validation["valid"] is True

    def test_no_library_preserves_safe_default(self, tmp_path, monkeypatch):
        calc = tmp_path / "calc"
        calc.mkdir()
        poscar = _write_poscar(calc / "POSCAR", "Si", "2")
        monkeypatch.delenv("SIMFLOW_VASP_POTCAR_PATH", raising=False)
        result = generate_potcar(str(poscar), str(calc / "POTCAR"))
        assert result["status"] == "unavailable"
        assert result["reason_code"] == "potcar_library_not_configured"
        assert not (calc / "POTCAR").exists()

    def test_unknown_explicit_profile_is_rejected_without_library(self, tmp_path, monkeypatch):
        calc = tmp_path / "calc"
        calc.mkdir()
        poscar = _write_poscar(calc / "POSCAR", "Si", "2")
        monkeypatch.delenv("SIMFLOW_VASP_POTCAR_PATH", raising=False)
        result = generate_potcar(
            str(poscar),
            str(calc / "POTCAR"),
            setups="future-profile",
        )
        assert result["reason_code"] == "unsupported_potcar_setup_profile"

    def test_rejects_simflow_and_project_root_destinations(self, tmp_path):
        library = _create_library(tmp_path / "potlib", {"Si": _potcar_text("Si")})
        poscar = _write_poscar(tmp_path / "POSCAR", "Si", "2")
        inside_state = generate_potcar(
            str(poscar),
            str(tmp_path / ".simflow" / "POTCAR"),
            potcar_root=str(library),
            project_root=str(tmp_path),
        )
        at_root = generate_potcar(
            str(poscar),
            str(tmp_path / "POTCAR"),
            potcar_root=str(library),
            project_root=str(tmp_path),
        )
        assert inside_state["reason_code"] == "restricted_potcar_output_location"
        assert at_root["reason_code"] == "restricted_potcar_output_location"

    def test_rejects_disguised_output_name_and_flavor_path_traversal(self, tmp_path):
        library = _create_library(tmp_path / "potlib", {"Si": _potcar_text("Si")})
        calc = tmp_path / "calc"
        calc.mkdir()
        poscar = _write_poscar(calc / "POSCAR", "Si", "2")

        disguised = generate_potcar(
            str(poscar),
            str(calc / "potential.dat"),
            potcar_root=str(library),
            project_root=str(tmp_path),
        )
        traversing = generate_potcar(
            str(poscar),
            str(calc / "POTCAR"),
            potcar_root=str(library),
            flavor="../private",
            project_root=str(tmp_path),
        )

        assert disguised["reason_code"] == "restricted_potcar_output_name"
        assert traversing["reason_code"] == "invalid_potcar_flavor"
        assert not (calc / "potential.dat").exists()
        assert not (calc / "POTCAR").exists()

    def test_existing_potcar_does_not_bypass_output_location_policy(self, tmp_path):
        poscar = _write_poscar(tmp_path / "POSCAR", "Si", "2")
        output = tmp_path / ".simflow" / "POTCAR"
        output.parent.mkdir()
        output.write_text(_potcar_text("Si"), encoding="utf-8")

        result = generate_potcar(
            str(poscar),
            str(output),
            project_root=str(tmp_path),
        )

        assert result["status"] == "error"
        assert result["reason_code"] == "restricted_potcar_output_location"


class TestValidatePotcar:
    def test_validates_element_and_exact_dataset_sequence(self, tmp_path):
        poscar = _write_poscar(tmp_path / "POSCAR", "Fe O", "1 1")
        potcar = tmp_path / "POTCAR"
        potcar.write_text(_potcar_text("Fe_pv") + _potcar_text("O"), encoding="utf-8")
        result = validate_potcar(str(poscar), str(potcar), expected_datasets=["Fe_pv", "O"])
        assert result["valid"] is True
        assert result["potcar_datasets"] == ["Fe_pv", "O"]
        assert result["content_included"] is False

    def test_dataset_mismatch_has_stable_reason(self, tmp_path):
        poscar = _write_poscar(tmp_path / "POSCAR", "Fe", "1")
        potcar = tmp_path / "POTCAR"
        potcar.write_text(_potcar_text("Fe_pv"), encoding="utf-8")
        result = validate_potcar(str(poscar), str(potcar), expected_datasets=["Fe"])
        assert result["valid"] is False
        assert result["reason_code"] == "existing_potcar_dataset_mismatch"


class TestEnvVars:
    def test_get_potcar_path(self, monkeypatch):
        monkeypatch.delenv("SIMFLOW_VASP_POTCAR_PATH", raising=False)
        assert get_potcar_path() is None
        monkeypatch.setenv("SIMFLOW_VASP_POTCAR_PATH", "/tmp/test")
        assert get_potcar_path() == "/tmp/test"

    def test_get_potcar_flavor(self, monkeypatch):
        monkeypatch.delenv("SIMFLOW_VASP_POTCAR_FLAVOR", raising=False)
        assert get_potcar_flavor() == "PBE"
        monkeypatch.setenv("SIMFLOW_VASP_POTCAR_FLAVOR", "LDA")
        assert get_potcar_flavor() == "LDA"
