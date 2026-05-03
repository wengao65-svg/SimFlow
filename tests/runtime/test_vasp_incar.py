#!/usr/bin/env python3
"""Tests for runtime/lib/vasp_incar.py — NBANDS strategy."""

import sys
from math import ceil
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "runtime"))

from lib.vasp_incar import (
    apply_nbands_policy,
    choose_nbands,
    estimate_vasp_default_nbands,
    get_explicit_user_nbands,
    nint_vasp,
    occupied_bands_estimate,
    validate_nbands,
)


# ── nint_vasp ──────────────────────────────────────────────────

class TestNintVasp:
    def test_round_down(self):
        assert nint_vasp(2.3) == 2

    def test_round_up(self):
        assert nint_vasp(2.7) == 3

    def test_half_integer(self):
        # VASP NINT rounds half-integers away from zero
        assert nint_vasp(2.5) == 3
        assert nint_vasp(3.5) == 4

    def test_exact_integer(self):
        assert nint_vasp(5.0) == 5


# ── occupied_bands_estimate ────────────────────────────────────

class TestOccupiedBandsEstimate:
    def test_nonmagnetic_even(self):
        # NELECT=32, ISPIN=1 -> 16 occupied
        assert occupied_bands_estimate(32, ispin=1) == 16

    def test_nonmagnetic_odd(self):
        # NELECT=33, ISPIN=1 -> 17 occupied
        assert occupied_bands_estimate(33, ispin=1) == 17

    def test_magnetic(self):
        # NELECT=32, MAGMOM=2 -> (32+2)/2 = 17
        assert occupied_bands_estimate(32, ispin=2, total_magmom=2.0) == 17

    def test_magnetic_negative_magmom(self):
        # NELECT=32, MAGMOM=-2 -> (32+2)/2 = 17 (abs)
        assert occupied_bands_estimate(32, ispin=2, total_magmom=-2.0) == 17

    def test_si_8atom(self):
        # Si 8-atom: ZVAL=4, NELECT=32, occupied=16
        assert occupied_bands_estimate(32) == 16


# ── estimate_vasp_default_nbands ──────────────────────────────

class TestEstimateVaspDefault:
    def test_si_8atom(self):
        # Si: NELECT=32, nions=8
        # nb1 = nint((32+2)/2) + max(8/2, 3) = nint(17) + 4 = 17 + 4 = 21
        # nb2 = 0.6 * 32 = 19.2
        # max(21, 19.2) = 21 -> ceil(21) = 21
        result = estimate_vasp_default_nbands(32, 8)
        assert result == 21

    def test_small_system(self):
        # NELECT=2, nions=1 (H atom)
        # nb1 = nint((2+2)/2) + max(1/2, 3) = nint(2) + 3 = 2 + 3 = 5
        # nb2 = 0.6 * 2 = 1.2
        # max(5, 1.2) = 5
        result = estimate_vasp_default_nbands(2, 1)
        assert result == 5

    def test_large_system(self):
        # NELECT=100, nions=25
        # nb1 = nint((100+2)/2) + max(25/2, 3) = nint(51) + 12.5 = 51 + 13 = 64
        # nb2 = 0.6 * 100 = 60
        # max(64, 60) = 64
        result = estimate_vasp_default_nbands(100, 25)
        assert result == 64

    def test_noncollinear_doubles(self):
        default_normal = estimate_vasp_default_nbands(32, 8, lnoncollinear=False)
        default_ncl = estimate_vasp_default_nbands(32, 8, lnoncollinear=True)
        assert default_ncl == 2 * default_normal

    def test_returns_int(self):
        result = estimate_vasp_default_nbands(33, 7)
        assert isinstance(result, int)


# ── validate_nbands ───────────────────────────────────────────

class TestValidateNbands:
    def test_valid_nbands(self):
        # occupied=16, NBANDS=20 -> OK
        validate_nbands(20, nelect=32)

    def test_too_small(self):
        # occupied=16, NBANDS=16 -> error
        with pytest.raises(ValueError, match="too small"):
            validate_nbands(16, nelect=32)

    def test_equal_to_occupied(self):
        # occupied=16, NBANDS=16 -> error (must be strictly greater)
        with pytest.raises(ValueError, match="too small"):
            validate_nbands(16, nelect=32)

    def test_minimum_valid(self):
        # occupied=16, NBANDS=17 -> OK
        validate_nbands(17, nelect=32)

    def test_magnetic_too_small(self):
        # occupied=ceil((32+2)/2)=17, NBANDS=17 -> error
        with pytest.raises(ValueError, match="too small"):
            validate_nbands(17, nelect=32, ispin=2, total_magmom=2.0)


# ── choose_nbands ─────────────────────────────────────────────

class TestChooseNbands:
    def test_scf_returns_none(self):
        assert choose_nbands("scf", nelect=32, nions=8) is None

    def test_relax_returns_none(self):
        assert choose_nbands("relax", nelect=32, nions=8) is None

    def test_static_returns_none(self):
        assert choose_nbands("static", nelect=32, nions=8) is None

    def test_bands_returns_none(self):
        assert choose_nbands("bands", nelect=32, nions=8) is None

    def test_band_alias_returns_none(self):
        # "band" is an alias for "bands"
        assert choose_nbands("band", nelect=32, nions=8) is None

    def test_dos_returns_none(self):
        assert choose_nbands("dos", nelect=32, nions=8) is None

    def test_nscf_returns_none(self):
        assert choose_nbands("nscf", nelect=32, nions=8) is None

    def test_case_insensitive(self):
        assert choose_nbands("SCF", nelect=32, nions=8) is None
        assert choose_nbands(" Bands ", nelect=32, nions=8) is None

    def test_optics_returns_2_5x(self):
        default = estimate_vasp_default_nbands(32, 8)
        result = choose_nbands("optics", nelect=32, nions=8)
        assert result == ceil(2.5 * default)

    def test_dielectric_returns_2_5x(self):
        default = estimate_vasp_default_nbands(32, 8)
        result = choose_nbands("dielectric", nelect=32, nions=8)
        assert result == ceil(2.5 * default)

    def test_eels_returns_2_5x(self):
        default = estimate_vasp_default_nbands(32, 8)
        result = choose_nbands("eels", nelect=32, nions=8)
        assert result == ceil(2.5 * default)

    def test_gw_returns_3x(self):
        default = estimate_vasp_default_nbands(32, 8)
        result = choose_nbands("gw", nelect=32, nions=8)
        assert result == ceil(3.0 * default)

    def test_rpa_returns_3x(self):
        default = estimate_vasp_default_nbands(32, 8)
        result = choose_nbands("rpa", nelect=32, nions=8)
        assert result == ceil(3.0 * default)

    def test_bse_returns_3x(self):
        default = estimate_vasp_default_nbands(32, 8)
        result = choose_nbands("bse", nelect=32, nions=8)
        assert result == ceil(3.0 * default)

    def test_wannier_returns_1_5x(self):
        default = estimate_vasp_default_nbands(32, 8)
        result = choose_nbands("wannier", nelect=32, nions=8)
        assert result == ceil(1.5 * default)

    def test_high_energy_window_returns_1_5x(self):
        default = estimate_vasp_default_nbands(32, 8)
        result = choose_nbands("scf", nelect=32, nions=8, high_energy_window=True)
        assert result == ceil(1.5 * default)

    def test_user_nbands_valid(self):
        result = choose_nbands("scf", nelect=32, nions=8, user_nbands=32)
        assert result == 32

    def test_user_nbands_too_small(self):
        with pytest.raises(ValueError, match="too small"):
            choose_nbands("scf", nelect=32, nions=8, user_nbands=16)

    def test_user_nbands_overrides_auto(self):
        # For optics, auto would be 2.5x, but user specifies 50
        result = choose_nbands("optics", nelect=32, nions=8, user_nbands=50)
        assert result == 50

    def test_unknown_calc_type_returns_none(self):
        # Unknown types fall through to None (fallback)
        assert choose_nbands("unknown_type", nelect=32, nions=8) is None


# ── get_explicit_user_nbands ──────────────────────────────────

class TestGetExplicitUserNbands:
    def test_no_nbands_key(self):
        assert get_explicit_user_nbands({}) is None
        assert get_explicit_user_nbands({"ENCUT": 520}) is None

    def test_numeric_value(self):
        assert get_explicit_user_nbands({"NBANDS": 32}) == 32

    def test_none_value(self):
        assert get_explicit_user_nbands({"NBANDS": None}) is None

    def test_auto_string(self):
        assert get_explicit_user_nbands({"NBANDS": "auto"}) is None

    def test_default_string(self):
        assert get_explicit_user_nbands({"NBANDS": "default"}) is None

    def test_empty_string(self):
        assert get_explicit_user_nbands({"NBANDS": ""}) is None

    def test_numeric_string(self):
        assert get_explicit_user_nbands({"NBANDS": "32"}) == 32


# ── apply_nbands_policy ───────────────────────────────────────

class TestApplyNbandsPolicy:
    def test_scf_removes_residual_nbands(self):
        incar = {"ENCUT": 520, "NBANDS": 16}
        result = apply_nbands_policy(incar, "scf", nelect=32, nions=8)
        assert "NBANDS" not in result
        assert result["ENCUT"] == 520

    def test_bands_removes_residual_nbands(self):
        incar = {"NBANDS": 20}
        result = apply_nbands_policy(incar, "bands", nelect=32, nions=8)
        assert "NBANDS" not in result

    def test_user_nbands_preserved(self):
        incar = {"ENCUT": 520}
        result = apply_nbands_policy(incar, "scf", nelect=32, nions=8, user_nbands=32)
        assert result["NBANDS"] == 32

    def test_optics_sets_nbands(self):
        incar = {"ENCUT": 520}
        result = apply_nbands_policy(incar, "optics", nelect=32, nions=8)
        default = estimate_vasp_default_nbands(32, 8)
        assert result["NBANDS"] == ceil(2.5 * default)

    def test_modifies_in_place(self):
        incar = {"NBANDS": 99}
        result = apply_nbands_policy(incar, "scf", nelect=32, nions=8)
        assert result is incar  # same object
        assert "NBANDS" not in incar
