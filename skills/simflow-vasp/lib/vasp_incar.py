"""VASP INCAR parameter strategies.

Provides automated parameter decisions for VASP INCAR files.
Currently implements NBANDS and NCORE/NPAR policies. Can be extended with
ISMEAR, ALGO, etc.

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

NCORE/NPAR policy (per VASP Wiki):
- Do not set NCORE and NPAR together unless the user explicitly supplied both.
- Unknown execution hardware: omit both and report missing execution context.
- GPU/OpenACC/OpenMP-offload execution: omit both by default. VASP resets
  NCORE to 1 on GPU/offload paths, and the GPU documentation recommends
  avoiding NCORE>1 for performance.
- Confirmed CPU execution: default to NPAR=4 unless the user requested a
  different parallelization policy.
- CPU NCORE mode requires evidence for the per-socket or per-NUMA-domain core
  count; otherwise report missing topology instead of guessing.
"""

from math import ceil, floor
import re
from typing import Any, Optional


# Calculation types that should NOT have NBANDS set by default.
_ORDINARY_CALC_TYPES = frozenset({
    "relax", "scf", "static", "bands", "band", "dos", "nscf",
})

_INCAR_POLICY_CONTROL_KEYS = frozenset({
    "ACCELERATOR",
    "ACCELERATOR_MODE",
    "CPU_CORES_PER_NUMA",
    "CPU_CORES_PER_NUMA_DOMAIN",
    "CPU_CORES_PER_SOCKET",
    "CPU_CORES_PER_CPU",
    "EXECUTION_CONTEXT",
    "EXECUTION_MODE",
    "HARDWARE_CONTEXT",
    "HARDWARE_MODE",
    "JOB_SCRIPT",
    "JOB_SCRIPT_PATH",
    "PARALLEL_PREFERENCE",
    "SCRIPT_LIBRARY_DIR",
    "SUBMIT_SCRIPT",
    "SUBMIT_SCRIPT_PATH",
    "VASP_ACCELERATOR",
    "VASP_EXECUTION_CONTEXT",
    "VASP_EXECUTION_MODE",
    "VASP_PARALLEL_PREFERENCE",
})

_ACCELERATED_CONTEXTS = frozenset({
    "accelerated", "accelerator", "gpu", "gpus", "cuda", "openacc",
    "openmp_offload", "openmp-offload", "omp_offload", "offload",
    "rocm", "hip", "oneapi_gpu",
})

_CPU_CONTEXTS = frozenset({"cpu", "cpu_only", "cpu-only", "host"})

_ACCELERATED_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"#SBATCH\s+.*--gpus(?:=|\b)",
        r"#SBATCH\s+.*--gres\s*=\s*gpu",
        r"#PBS\s+.*(?:ngpus|gpus)\s*[=:]",
        r"\bCUDA_VISIBLE_DEVICES\b",
        r"\bROCR_VISIBLE_DEVICES\b",
        r"\bHIP_VISIBLE_DEVICES\b",
        r"\bZE_AFFINITY_MASK\b",
        r"\bMPICH_GPU_SUPPORT_ENABLED\s*=\s*1\b",
        r"\bI_MPI_OFFLOAD\s*=\s*1\b",
        r"\bHSA_XNACK\b",
        r"\bOMP_TARGET_OFFLOAD\b",
        r"\bopenacc\b",
        r"\bomp[_-]?off(load)?\b",
        r"\bnvhpc.*acc\b",
        r"\brocm\b",
        r"\bcuda\b",
        r"\bgpu\b",
        r"\bvasp[_-]?(?:gpu|acc|openacc|omp[_-]?off)\b",
    )
]


def _param_value(params: dict[str, Any], *names: str) -> Any:
    """Return a value from params by case-insensitive key lookup."""
    wanted = {name.upper() for name in names}
    for key, value in params.items():
        if str(key).upper() in wanted:
            return value
    return None


def _has_param(params: dict[str, Any], *names: str) -> bool:
    wanted = {name.upper() for name in names}
    return any(str(key).upper() in wanted for key in params)


def _is_sentinel(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return value.lower().strip() in {"", "auto", "default", "omit", "none", "null"}
    return False


def _as_int(value: Any, tag: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{tag} must be an integer, got {value!r}.") from exc


def _normalize_execution_context(value: Any) -> Optional[str]:
    if _is_sentinel(value):
        return None
    text = str(value).strip().lower().replace(" ", "_")
    if text in _CPU_CONTEXTS:
        return "cpu"
    if text in _ACCELERATED_CONTEXTS:
        return "accelerated"
    return None


def _normalize_parallel_preference(value: Any) -> str:
    if _is_sentinel(value):
        return "npar"
    text = str(value).strip().lower().replace(" ", "_")
    if text in {"ncore", "core"}:
        return "ncore"
    if text in {"npar", "par", "default", "cpu_default"}:
        return "npar"
    if text in {"omit", "none", "no_parallel_tags", "no_tags"}:
        return "omit"
    raise ValueError(
        "parallel_preference must be one of npar, ncore, or omit "
        f"(got {value!r})."
    )


def filter_vasp_incar_params(params: dict[str, Any]) -> dict[str, Any]:
    """Remove SimFlow policy/control keys before writing INCAR parameters."""
    return {
        key: value
        for key, value in (params or {}).items()
        if str(key).upper() not in _INCAR_POLICY_CONTROL_KEYS
    }


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
    if not _has_param(params, "NBANDS"):
        return None
    value = _param_value(params, "NBANDS")
    if _is_sentinel(value):
        return None
    return int(value)


def get_explicit_user_parallel_tag(params: dict, tag: str) -> Optional[int]:
    """Extract an explicit NCORE or NPAR value from user parameters."""
    tag_norm = tag.upper()
    if tag_norm not in {"NCORE", "NPAR"}:
        raise ValueError(f"Unsupported VASP parallel tag: {tag}")
    if not _has_param(params, tag_norm):
        return None
    value = _param_value(params, tag_norm)
    if _is_sentinel(value):
        return None
    return _as_int(value, tag_norm)


def infer_vasp_execution_context(
    params: dict[str, Any] | None = None,
    *,
    job_script_text: str | None = None,
    modules: list[str] | tuple[str, ...] | None = None,
    executable: str | None = None,
    command: str | None = None,
) -> dict[str, Any]:
    """Infer whether a VASP run is CPU-only or accelerator-backed.

    This is intentionally conservative. It treats explicit user metadata as
    authoritative, recognizes clear GPU/offload evidence in submit scripts and
    module/executable hints, and otherwise returns ``unknown``.
    """
    params = params or {}
    explicit = _param_value(
        params,
        "VASP_EXECUTION_MODE",
        "VASP_EXECUTION_CONTEXT",
        "EXECUTION_MODE",
        "EXECUTION_CONTEXT",
        "HARDWARE_MODE",
        "HARDWARE_CONTEXT",
        "ACCELERATOR_MODE",
        "VASP_ACCELERATOR",
        "ACCELERATOR",
    )
    normalized = _normalize_execution_context(explicit)
    if normalized:
        return {
            "context": normalized,
            "source": "explicit_user_parameter",
            "confidence": "high",
            "evidence": [str(explicit)],
            "warnings": [],
        }
    if explicit is not None and not _is_sentinel(explicit):
        return {
            "context": "unknown",
            "source": "explicit_user_parameter",
            "confidence": "low",
            "evidence": [str(explicit)],
            "warnings": [f"Unrecognized VASP execution context: {explicit!r}."],
        }

    evidence_text = "\n".join(
        item
        for item in [
            job_script_text or "",
            " ".join(str(module) for module in (modules or [])),
            executable or "",
            command or "",
        ]
        if item
    )
    matched = []
    for pattern in _ACCELERATED_PATTERNS:
        match = pattern.search(evidence_text)
        if match:
            matched.append(match.group(0))
    if matched:
        return {
            "context": "accelerated",
            "source": "submit_or_environment_evidence",
            "confidence": "medium",
            "evidence": sorted(set(matched))[:8],
            "warnings": [],
        }

    return {
        "context": "unknown",
        "source": "insufficient_evidence",
        "confidence": "none",
        "evidence": [],
        "warnings": [],
    }


def apply_ncore_npar_policy(
    incar: dict,
    params: dict[str, Any] | None = None,
    *,
    job_script_text: str | None = None,
    modules: list[str] | tuple[str, ...] | None = None,
    executable: str | None = None,
    command: str | None = None,
) -> dict[str, Any]:
    """Apply VASP NCORE/NPAR policy to an INCAR parameter dict.

    The dict is modified in-place. Residual/template NCORE/NPAR values are
    removed first; user-explicit values are then restored according to policy.
    The returned report tells callers whether hardware context is still needed.
    """
    params = params or {}
    report = {
        "status": "pass",
        "execution_context": None,
        "context_source": None,
        "actions": [],
        "warnings": [],
        "missing_information": [],
    }

    user_ncore = get_explicit_user_parallel_tag(params, "NCORE")
    user_npar = get_explicit_user_parallel_tag(params, "NPAR")
    user_supplied_ncore = user_ncore is not None
    user_supplied_npar = user_npar is not None

    incar.pop("NCORE", None)
    incar.pop("NPAR", None)
    report["actions"].append("removed_residual_ncore_npar")

    context = infer_vasp_execution_context(
        params,
        job_script_text=job_script_text,
        modules=modules,
        executable=executable,
        command=command,
    )
    report["execution_context"] = context["context"]
    report["context_source"] = context["source"]
    report["warnings"].extend(context.get("warnings", []))

    if user_supplied_ncore and user_supplied_npar:
        incar["NCORE"] = user_ncore
        incar["NPAR"] = user_npar
        report["status"] = "warning"
        report["actions"].append("preserved_user_explicit_ncore_and_npar")
        report["warnings"].append(
            "NCORE and NPAR were both user-specified. VASP treats them as "
            "inverse controls and NPAR takes precedence; benchmark before production."
        )
        if context["context"] == "accelerated":
            report["warnings"].append(
                "Accelerated VASP paths normally omit NCORE/NPAR; explicit "
                "values were preserved because the user supplied them."
            )
        return report

    if user_supplied_ncore:
        incar["NCORE"] = user_ncore
        report["actions"].append("preserved_user_explicit_ncore")
        if context["context"] == "accelerated":
            report["status"] = "warning"
            report["warnings"].append(
                "Accelerated VASP paths reset or avoid NCORE; explicit NCORE "
                "was preserved because the user supplied it."
            )
        return report

    if user_supplied_npar:
        incar["NPAR"] = user_npar
        report["actions"].append("preserved_user_explicit_npar")
        if context["context"] == "accelerated":
            report["status"] = "warning"
            report["warnings"].append(
                "Accelerated VASP paths normally omit NPAR; explicit NPAR "
                "was preserved because the user supplied it."
            )
        return report

    if context["context"] == "accelerated":
        report["actions"].append("omitted_ncore_npar_for_accelerated_execution")
        return report

    if context["context"] == "cpu":
        preference = _normalize_parallel_preference(
            _param_value(params, "VASP_PARALLEL_PREFERENCE", "PARALLEL_PREFERENCE")
        )
        if preference == "omit":
            report["actions"].append("omitted_ncore_npar_by_user_preference")
            return report
        if preference == "npar":
            incar["NPAR"] = 4
            report["actions"].append("set_cpu_default_npar_4")
            return report

        core_count = _param_value(
            params,
            "CPU_CORES_PER_NUMA",
            "CPU_CORES_PER_NUMA_DOMAIN",
            "CPU_CORES_PER_SOCKET",
            "CPU_CORES_PER_CPU",
        )
        if _is_sentinel(core_count):
            report["status"] = "needs_inputs"
            report["missing_information"].append(
                "cpu_cores_per_socket_or_numa_domain"
            )
            report["actions"].append("omitted_ncore_until_cpu_topology_is_known")
            return report
        incar["NCORE"] = _as_int(core_count, "CPU_CORES_PER_SOCKET")
        report["actions"].append("set_cpu_ncore_from_topology")
        return report

    report["status"] = "needs_inputs"
    report["missing_information"].append(
        "vasp execution context: cpu or accelerated/openacc/gpu/offload"
    )
    report["actions"].append("omitted_ncore_npar_until_execution_context_is_known")
    return report


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
