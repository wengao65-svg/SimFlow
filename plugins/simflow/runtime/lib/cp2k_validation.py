"""CP2K input and dependency validation for common SimFlow tasks."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .cp2k_input import read_cif_to_xyz, read_xyz_structure


TASK_ALIASES = {
    "single_point": "energy",
    "singlepoint": "energy",
    "sp": "energy",
    "geoopt": "geo_opt",
    "cellopt": "cell_opt",
    "nvt": "aimd_nvt",
    "nve": "aimd_nve",
    "npt": "aimd_npt",
    "md_nvt": "aimd_nvt",
    "md_nve": "aimd_nve",
    "md_npt": "aimd_npt",
    "continue": "restart",
    "continuation": "restart",
}

SUPPORTED_TASKS = {
    "energy",
    "geo_opt",
    "cell_opt",
    "aimd_nvt",
    "aimd_nve",
    "aimd_npt",
    "restart",
    "parse",
    "troubleshoot",
}

EXPECTED_RUN_TYPES = {
    "energy": "ENERGY",
    "geo_opt": "GEO_OPT",
    "cell_opt": "CELL_OPT",
    "aimd_nvt": "MD",
    "aimd_nve": "MD",
    "aimd_npt": "MD",
}

EXPECTED_MOTION_SECTIONS = {
    "GEO_OPT": ("MOTION", "GEO_OPT"),
    "CELL_OPT": ("MOTION", "CELL_OPT"),
    "MD": ("MOTION", "MD"),
}


@dataclass
class ParsedCP2KInput:
    sections: set[tuple[str, ...]] = field(default_factory=set)
    keywords: dict[tuple[str, ...], dict[str, list[str]]] = field(default_factory=dict)
    kind_elements: list[str] = field(default_factory=list)


def normalize_cp2k_task(task: str) -> str:
    """Normalize a task label for validation/planning."""
    normalized = task.strip().lower().replace("-", "_").replace(" ", "_")
    normalized = TASK_ALIASES.get(normalized, normalized)
    if normalized not in SUPPORTED_TASKS:
        supported = ", ".join(sorted(SUPPORTED_TASKS))
        raise ValueError(f"Unknown CP2K task: {task}. Supported values: {supported}.")
    return normalized


def parse_cp2k_input_text(content: str) -> ParsedCP2KInput:
    """Parse the sections and keywords of a CP2K input deck."""
    parsed = ParsedCP2KInput()
    stack: list[str] = []

    for raw_line in content.splitlines():
        line = _strip_comments(raw_line)
        if not line:
            continue

        if line.startswith("&END"):
            if stack:
                stack.pop()
            continue

        if line.startswith("&"):
            parts = line[1:].split()
            section = parts[0].upper()
            stack.append(section)
            path = tuple(stack)
            parsed.sections.add(path)
            if section == "KIND" and len(parts) > 1:
                parsed.kind_elements.append(parts[1])
            continue

        parts = line.split(None, 1)
        key = parts[0].upper()
        value = parts[1].strip() if len(parts) > 1 else ""
        path = tuple(stack)
        parsed.keywords.setdefault(path, {}).setdefault(key, []).append(value)

    return parsed


def validate_cp2k_inputs(
    task: str,
    calc_dir: str,
    input_path: str | None = None,
    input_text: str | None = None,
) -> dict[str, Any]:
    """Validate a CP2K input deck and its lightweight file dependencies."""
    task_norm = normalize_cp2k_task(task)
    base = Path(calc_dir).expanduser().resolve()
    deck_path = Path(input_path).expanduser().resolve() if input_path else _default_input_path(base)

    if task_norm in {"parse", "troubleshoot"} and input_text is None and deck_path is None:
        return {
            "status": "skip",
            "valid": True,
            "task": task_norm,
            "calc_dir": str(base),
            "input_path": None,
            "checks": [{
                "check": "input_optional_for_output_only_task",
                "passed": True,
                "message": "No CP2K input deck was required for this output-only task.",
            }],
            "detected": {},
        }

    if input_text is None:
        if deck_path is None or not deck_path.is_file():
            return {
                "status": "fail",
                "valid": False,
                "task": task_norm,
                "calc_dir": str(base),
                "input_path": str(deck_path) if deck_path else None,
                "checks": [{
                    "check": "input_deck_exists",
                    "passed": False,
                    "message": "CP2K input deck not found.",
                }],
                "detected": {},
            }
        input_text = deck_path.read_text(encoding="utf-8", errors="replace")

    parsed = parse_cp2k_input_text(input_text)
    run_type = _keyword(parsed, ("GLOBAL",), "RUN_TYPE")
    basis_file = _keyword(parsed, ("FORCE_EVAL", "DFT"), "BASIS_SET_FILE_NAME")
    potential_file = _keyword(parsed, ("FORCE_EVAL", "DFT"), "POTENTIAL_FILE_NAME")
    coord_file = _keyword(parsed, ("FORCE_EVAL", "SUBSYS", "TOPOLOGY"), "COORD_FILE_NAME")
    coord_format = (_keyword(parsed, ("FORCE_EVAL", "SUBSYS", "TOPOLOGY"), "COORD_FILE_FORMAT") or "XYZ").upper()
    restart_file = _keyword(parsed, ("EXT_RESTART",), "RESTART_FILE_NAME")
    scf_guess = _keyword(parsed, ("FORCE_EVAL", "DFT", "SCF"), "SCF_GUESS")

    checks = [
        _check(
            "global_run_type",
            bool(run_type),
            "GLOBAL/RUN_TYPE found." if run_type else "GLOBAL/RUN_TYPE is missing.",
        ),
        _check(
            "force_eval_dft",
            _has_section(parsed, ("FORCE_EVAL", "DFT")),
            "FORCE_EVAL/DFT section found." if _has_section(parsed, ("FORCE_EVAL", "DFT")) else "FORCE_EVAL/DFT section is missing.",
        ),
        _check(
            "basis_set_file_name",
            bool(basis_file),
            "BASIS_SET_FILE_NAME found." if basis_file else "BASIS_SET_FILE_NAME is missing.",
        ),
        _check(
            "potential_file_name",
            bool(potential_file),
            "POTENTIAL_FILE_NAME found." if potential_file else "POTENTIAL_FILE_NAME is missing.",
        ),
        _check(
            "mgrid",
            _has_section(parsed, ("FORCE_EVAL", "DFT", "MGRID")),
            "MGRID section found." if _has_section(parsed, ("FORCE_EVAL", "DFT", "MGRID")) else "MGRID section is missing.",
        ),
        _check(
            "scf",
            _has_section(parsed, ("FORCE_EVAL", "DFT", "SCF")),
            "SCF section found." if _has_section(parsed, ("FORCE_EVAL", "DFT", "SCF")) else "SCF section is missing.",
        ),
        _check(
            "ot",
            _has_section(parsed, ("FORCE_EVAL", "DFT", "SCF", "OT")),
            "OT section found." if _has_section(parsed, ("FORCE_EVAL", "DFT", "SCF", "OT")) else "OT section is missing.",
        ),
        _check(
            "xc",
            _has_section(parsed, ("FORCE_EVAL", "DFT", "XC")),
            "XC section found." if _has_section(parsed, ("FORCE_EVAL", "DFT", "XC")) else "XC section is missing.",
        ),
        _check(
            "subsys_cell",
            _has_section(parsed, ("FORCE_EVAL", "SUBSYS", "CELL")),
            "SUBSYS/CELL section found." if _has_section(parsed, ("FORCE_EVAL", "SUBSYS", "CELL")) else "SUBSYS/CELL section is missing.",
        ),
        _check(
            "coord_topology",
            _has_section(parsed, ("FORCE_EVAL", "SUBSYS", "TOPOLOGY")) and bool(coord_file),
            "SUBSYS/TOPOLOGY with COORD_FILE_NAME found."
            if _has_section(parsed, ("FORCE_EVAL", "SUBSYS", "TOPOLOGY")) and coord_file
            else "SUBSYS/TOPOLOGY or COORD_FILE_NAME is missing.",
        ),
    ]

    expected_run_type = EXPECTED_RUN_TYPES.get(task_norm)
    if expected_run_type:
        checks.append(_check(
            "task_run_type_match",
            run_type == expected_run_type,
            f"Task expects RUN_TYPE {expected_run_type} and found {run_type}."
            if run_type == expected_run_type
            else f"Task expects RUN_TYPE {expected_run_type} but found {run_type or 'missing'}.",
        ))

    motion_ok, motion_message = _validate_motion_for_run_type(parsed, run_type)
    checks.append(_check("run_type_motion_match", motion_ok, motion_message))

    coord_path = _resolve_relative_path(coord_file, base, deck_path.parent if deck_path else base)
    coord_exists = coord_path.is_file() if coord_path else False
    checks.append(_check(
        "coord_file_exists",
        coord_exists,
        f"Coordinate file found: {coord_path.name}."
        if coord_exists and coord_path is not None
        else f"Coordinate file not found: {coord_file or 'missing in input deck'}.",
    ))

    kind_ok = False
    kind_message = "Could not verify KIND coverage because coordinates are unavailable."
    coord_elements: list[str] = []
    if coord_exists and coord_path is not None:
        try:
            coord_elements = _read_coord_elements(coord_path, coord_format)
        except ValueError as exc:
            kind_message = str(exc)
        else:
            missing = sorted(set(coord_elements) - set(parsed.kind_elements))
            kind_ok = not missing
            kind_message = (
                "KIND blocks cover all elements in the coordinate file."
                if kind_ok
                else f"KIND blocks are missing elements: {', '.join(missing)}."
            )
    checks.append(_check("kind_coverage", kind_ok, kind_message))

    restart_required = bool(restart_file) or (scf_guess or "").upper() == "RESTART" or task_norm == "restart"
    if restart_required:
        restart_path = _resolve_relative_path(restart_file, base, deck_path.parent if deck_path else base)
        restart_exists = restart_path.is_file() if restart_path else False
        checks.append(_check(
            "restart_file_exists",
            restart_exists,
            f"Restart file found: {restart_path.name}."
            if restart_exists and restart_path is not None
            else f"Restart file not found: {restart_file or 'missing in input deck'}.",
        ))

    return {
        "status": "pass" if all(check["passed"] for check in checks) else "fail",
        "valid": all(check["passed"] for check in checks),
        "task": task_norm,
        "calc_dir": str(base),
        "input_path": str(deck_path) if deck_path else None,
        "checks": checks,
        "detected": {
            "run_type": run_type,
            "basis_set_file": basis_file,
            "potential_file": potential_file,
            "coord_file": coord_file,
            "coord_format": coord_format,
            "restart_file": restart_file,
            "scf_guess": scf_guess,
            "kind_elements": sorted(set(parsed.kind_elements)),
            "coord_elements": sorted(set(coord_elements)),
        },
    }


def _default_input_path(calc_dir: Path) -> Path | None:
    candidates = sorted(calc_dir.glob("*.inp"))
    if not candidates:
        return None
    return candidates[0]


def _strip_comments(line: str) -> str:
    for marker in ("!", "#"):
        if marker in line:
            line = line.split(marker, 1)[0]
    return line.strip()


def _has_section(parsed: ParsedCP2KInput, section_path: tuple[str, ...]) -> bool:
    return section_path in parsed.sections


def _keyword(parsed: ParsedCP2KInput, section_path: tuple[str, ...], key: str) -> str | None:
    values = parsed.keywords.get(section_path, {}).get(key.upper())
    if not values:
        return None
    return values[-1]


def _validate_motion_for_run_type(parsed: ParsedCP2KInput, run_type: str | None) -> tuple[bool, str]:
    if run_type is None:
        return False, "Cannot validate MOTION because RUN_TYPE is missing."
    normalized = run_type.upper()
    if normalized == "ENERGY":
        has_motion = any(path[0] == "MOTION" for path in parsed.sections if path)
        if has_motion:
            return False, "RUN_TYPE ENERGY should not include MOTION/MD or optimization motion sections."
        return True, "RUN_TYPE ENERGY correctly omits MOTION."

    expected = EXPECTED_MOTION_SECTIONS.get(normalized)
    if not expected:
        return True, f"No explicit MOTION rule enforced for RUN_TYPE {normalized}."
    if _has_section(parsed, expected):
        return True, f"RUN_TYPE {normalized} matches {expected[-1]} motion section."
    return False, f"RUN_TYPE {normalized} requires {'/'.join(expected)}."


def _resolve_relative_path(name: str | None, calc_dir: Path, input_dir: Path) -> Path | None:
    if not name:
        return None
    candidate = Path(name)
    if candidate.is_absolute():
        return candidate
    input_relative = input_dir / candidate
    if input_relative.exists():
        return input_relative
    return calc_dir / candidate


def _read_coord_elements(coord_path: Path, coord_format: str) -> list[str]:
    if coord_format == "CIF" or coord_path.suffix.lower() == ".cif":
        _, _, counts = read_cif_to_xyz(coord_path)
        return sorted(counts)
    _, counts, _ = read_xyz_structure(coord_path)
    return sorted(counts)


def _check(name: str, passed: bool, message: str) -> dict[str, Any]:
    return {"check": name, "passed": bool(passed), "message": message}
