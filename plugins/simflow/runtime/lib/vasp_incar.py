"""VASP INCAR parameter strategies.

Provides automated parameter decisions for VASP INCAR files.
Currently implements NBANDS policy. Can be extended with ISMEAR, ALGO, etc.

This module operates on dicts and parameter values only — it does not read
or write INCAR files.

NBANDS policy (per VASP Wiki):
- Ordinary calculations (relax, scf, static, bands, dos, nscf): do not write
  NBANDS. Let VASP use its default value.
- If the user explicitly provides NBANDS, validate NBANDS > occupied_bands.
- LOPTICS / dielectric / EELS: 2–3× VASP default.
- GW / RPA / BSE / cRPA: 3× VASP default, with convergence test warning.
- Wannier / high-energy window: 1.5× VASP default.
- NELECT must come from POTCAR ZVAL (valence electrons), not atomic number
  total electrons.
"""

from math import ceil, floor
from typing import Optional


# Calculation types that should NOT have NBANDS set by default.
_ORDINARY_CALC_TYPES = frozenset({
    "relax", "scf", "static", "bands", "band", "dos", "nscf",
})


def nint_vasp(x: float) -> int:
    """Approximate VASP's NINT (nearest integer) for positive numbers.

    VASP uses Fortran NINT which rounds half-integers away from zero.
    For positive x: floor(x + 0.5).
    """
    return floor(x + 0.5)


def estimate_vasp_default_nbands(nelect: float, nions: int,
                                  lnoncollinear: bool = False) -> int:
    """Estimate VASP's default NBANDS value.

    VASP default formula (from VASP Wiki / source):
        NBANDS = max(
            nint((NELECT + 2) / 2) + max(nions / 2, 3),
            0.6 * NELECT
        )
    Rounded up to the nearest integer. For noncollinear calculations,
    multiply by 2.

    Args:
        nelect: Number of valence electrons (from POTCAR ZVAL, not atomic number)
        nions: Number of ions/atoms in the cell
        lnoncollinear: Whether noncollinear magnetism is enabled

    Returns:
        Estimated default NBANDS
    """
    nb1 = nint_vasp((nelect + 2) / 2) + max(nions / 2, 3)
    nb2 = 0.6 * nelect
    nbands = ceil(max(nb1, nb2))

    if lnoncollinear:
        nbands *= 2

    return nbands


def occupied_bands_estimate(nelect: float, ispin: int = 1,
                             total_magmom: Optional[float] = None) -> int:
    """Estimate the number of occupied bands.

    For non-spin-polarized (ISPIN=1):
        occupied = ceil(NELECT / 2)
    For spin-polarized (ISPIN=2) with total magnetic moment:
        occupied = ceil((NELECT + |MAGMOM|) / 2)
        (majority spin channel has more electrons)

    Args:
        nelect: Number of valence electrons
        ispin: Spin polarization (1=non-mag, 2=spin-polarized)
        total_magmom: Total magnetic moment (ISPIN=2 only)

    Returns:
        Estimated number of occupied bands
    """
    if ispin == 2 and total_magmom is not None:
        return ceil((nelect + abs(total_magmom)) / 2)
    return ceil(nelect / 2)


def validate_nbands(nbands: int, nelect: float, ispin: int = 1,
                     total_magmom: Optional[float] = None) -> None:
    """Validate that NBANDS is large enough.

    NBANDS must be strictly greater than the number of occupied bands.
    Raises ValueError if too small.

    Args:
        nbands: User-specified NBANDS value
        nelect: Number of valence electrons
        ispin: Spin polarization
        total_magmom: Total magnetic moment (ISPIN=2 only)

    Raises:
        ValueError: If NBANDS <= occupied_bands
    """
    occupied = occupied_bands_estimate(nelect, ispin, total_magmom)
    if nbands <= occupied:
        raise ValueError(
            f"NBANDS={nbands} is too small. "
            f"For NELECT={nelect}, occupied_bands≈{occupied}. "
            f"Need NBANDS > {occupied}, or omit NBANDS to use VASP default."
        )


def choose_nbands(calc_type: str, nelect: float, nions: int,
                  user_nbands: Optional[int] = None,
                  ispin: int = 1,
                  total_magmom: Optional[float] = None,
                  lnoncollinear: bool = False,
                  high_energy_window: bool = False) -> Optional[int]:
    """Choose NBANDS value based on calculation type and parameters.

    Args:
        calc_type: Calculation type (scf, relax, bands, optics, gw, etc.)
        nelect: Number of valence electrons (from POTCAR ZVAL)
        nions: Number of ions/atoms
        user_nbands: User explicitly specified NBANDS (None if not specified)
        ispin: Spin polarization (1 or 2)
        total_magmom: Total magnetic moment (ISPIN=2)
        lnoncollinear: Noncollinear magnetism
        high_energy_window: Whether high-energy conduction bands are needed

    Returns:
        None — do not write NBANDS (ordinary calculations)
        int  — NBANDS value to write into INCAR

    Raises:
        ValueError: If user_nbands is specified but too small
    """
    calc = calc_type.lower().strip()

    # Alias: "band" -> "bands"
    if calc == "band":
        calc = "bands"

    # Estimate VASP default for reference
    nbands_default = estimate_vasp_default_nbands(
        nelect=nelect, nions=nions, lnoncollinear=lnoncollinear,
    )

    # User explicitly specified: accept but validate
    if user_nbands is not None:
        validate_nbands(user_nbands, nelect, ispin, total_magmom)
        return int(user_nbands)

    # Ordinary calculations: do not write NBANDS
    if calc in _ORDINARY_CALC_TYPES and not high_energy_window:
        return None

    # LOPTICS / dielectric / EELS: 2.5× default
    if calc in {"optics", "dielectric", "eels"}:
        return ceil(2.5 * nbands_default)

    # GW / RPA / BSE / cRPA: 3× default
    if calc in {"gw", "rpa", "bse", "crpa"}:
        return ceil(3.0 * nbands_default)

    # Wannier or high-energy window: 1.5× default
    if calc in {"wannier"} or high_energy_window:
        return ceil(1.5 * nbands_default)

    # Fallback: do not write
    return None


def get_explicit_user_nbands(params: dict) -> Optional[int]:
    """Extract user-explicit NBANDS from parameters.

    Distinguishes between "user explicitly set NBANDS=32" vs "template/default
    left a residual NBANDS key". Returns None for sentinel values that should
    be treated as "not specified".

    Args:
        params: Parameter dict (INCAR overrides)

    Returns:
        None if NBANDS not explicitly set or is a sentinel value
        int if user explicitly set a numeric NBANDS
    """
    if "NBANDS" not in params:
        return None
    value = params["NBANDS"]
    if value is None:
        return None
    if isinstance(value, str) and value.lower().strip() in ("", "auto", "default"):
        return None
    return int(value)


def apply_nbands_policy(incar: dict, calc_type: str, nelect: float,
                         nions: int, user_nbands: Optional[int] = None,
                         ispin: int = 1,
                         total_magmom: Optional[float] = None,
                         lnoncollinear: bool = False,
                         high_energy_window: bool = False) -> dict:
    """Apply NBANDS policy to an INCAR parameter dict.

    Modifies the dict in-place and returns it. For ordinary calculations
    where NBANDS should not be set, removes any residual NBANDS key.

    Args:
        incar: INCAR parameter dict (modified in-place)
        calc_type: Calculation type
        nelect: Number of valence electrons (from POTCAR ZVAL)
        nions: Number of ions/atoms
        user_nbands: User-explicit NBANDS (None if not specified)
        ispin: Spin polarization
        total_magmom: Total magnetic moment
        lnoncollinear: Noncollinear magnetism
        high_energy_window: Whether high-energy conduction bands are needed

    Returns:
        The modified incar dict
    """
    nbands = choose_nbands(
        calc_type=calc_type,
        nelect=nelect,
        nions=nions,
        user_nbands=user_nbands,
        ispin=ispin,
        total_magmom=total_magmom,
        lnoncollinear=lnoncollinear,
        high_energy_window=high_energy_window,
    )

    if nbands is not None:
        incar["NBANDS"] = nbands
    else:
        incar.pop("NBANDS", None)

    return incar
