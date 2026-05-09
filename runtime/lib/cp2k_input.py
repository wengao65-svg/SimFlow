"""CP2K input generation and lightweight structure handling.

This module intentionally covers only common SimFlow orchestration tasks:
single point energy, geometry optimization, basic cell optimization, and
basic AIMD ensembles (NVT/NVE/NPT). It does not try to expose the full CP2K
parameter space or replace the official CP2K manual.
"""

from __future__ import annotations

import math
import re
from pathlib import Path
from typing import Iterable


SUPPORTED_CALC_TYPES = (
    "energy",
    "geo_opt",
    "cell_opt",
    "aimd_nvt",
    "aimd_nve",
    "aimd_npt",
)

CALC_TYPE_ALIASES = {
    "single_point": "energy",
    "singlepoint": "energy",
    "sp": "energy",
    "geoopt": "geo_opt",
    "geometry_optimization": "geo_opt",
    "geometry_opt": "geo_opt",
    "cellopt": "cell_opt",
    "cell_optimization": "cell_opt",
    "nvt": "aimd_nvt",
    "nve": "aimd_nve",
    "npt": "aimd_npt",
    "md_nvt": "aimd_nvt",
    "md_nve": "aimd_nve",
    "md_npt": "aimd_npt",
}


DEFAULT_ELEMENT_PARAMS = {
    "H": {"basis": "DZVP-MOLOPT-SR-GTH", "potential": "GTH-PBE-q1"},
    "He": {"basis": "DZVP-MOLOPT-SR-GTH", "potential": "GTH-PBE-q2"},
    "Li": {"basis": "DZVP-MOLOPT-SR-GTH", "potential": "GTH-PBE-q3"},
    "Be": {"basis": "DZVP-MOLOPT-SR-GTH", "potential": "GTH-PBE-q4"},
    "B": {"basis": "DZVP-MOLOPT-SR-GTH", "potential": "GTH-PBE-q3"},
    "C": {"basis": "DZVP-MOLOPT-SR-GTH", "potential": "GTH-PBE-q4"},
    "N": {"basis": "DZVP-MOLOPT-SR-GTH", "potential": "GTH-PBE-q5"},
    "O": {"basis": "DZVP-MOLOPT-SR-GTH", "potential": "GTH-PBE-q6"},
    "F": {"basis": "DZVP-MOLOPT-SR-GTH", "potential": "GTH-PBE-q7"},
    "Ne": {"basis": "DZVP-MOLOPT-SR-GTH", "potential": "GTH-PBE-q8"},
    "Na": {"basis": "DZVP-MOLOPT-SR-GTH", "potential": "GTH-PBE-q9"},
    "Mg": {"basis": "DZVP-MOLOPT-SR-GTH", "potential": "GTH-PBE-q2"},
    "Al": {"basis": "DZVP-MOLOPT-SR-GTH", "potential": "GTH-PBE-q3"},
    "Si": {"basis": "DZVP-MOLOPT-SR-GTH", "potential": "GTH-PBE-q4"},
    "P": {"basis": "DZVP-MOLOPT-SR-GTH", "potential": "GTH-PBE-q5"},
    "S": {"basis": "DZVP-MOLOPT-SR-GTH", "potential": "GTH-PBE-q6"},
    "Cl": {"basis": "DZVP-MOLOPT-SR-GTH", "potential": "GTH-PBE-q7"},
    "Ar": {"basis": "DZVP-MOLOPT-SR-GTH", "potential": "GTH-PBE-q8"},
    "K": {"basis": "DZVP-MOLOPT-SR-GTH", "potential": "GTH-PBE-q9"},
    "Ca": {"basis": "DZVP-MOLOPT-SR-GTH", "potential": "GTH-PBE-q10"},
}


def normalize_calc_type(calc_type: str) -> str:
    """Normalize a user-facing task label to a supported CP2K task."""
    normalized = calc_type.strip().lower().replace("-", "_").replace(" ", "_")
    normalized = CALC_TYPE_ALIASES.get(normalized, normalized)
    if normalized not in SUPPORTED_CALC_TYPES:
        supported = ", ".join(SUPPORTED_CALC_TYPES)
        raise ValueError(f"Unknown calc_type: {calc_type}. Supported values: {supported}.")
    return normalized


def cp2k_defaults(calc_type: str = "aimd_nvt") -> dict:
    """Return SimFlow defaults for a common CP2K task."""
    task = normalize_calc_type(calc_type)
    base = {
        "print_level": "LOW",
        "project_name": f"cp2k_{task}",
        "basis_set_file": "BASIS_MOLOPT",
        "potential_file": "POTENTIAL",
        "charge": 0,
        "multiplicity": 1,
        "cutoff": 400,
        "rel_cutoff": 50,
        "qs_eps_default": 1.0e-8,
        "max_scf": 50,
        "eps_scf": 1.0e-6,
        "scf_guess": "ATOMIC",
        "ot_minimizer": "DIIS",
        "ot_preconditioner": "FULL_SINGLE_INVERSE",
        "outer_max_scf": 20,
        "outer_eps_scf": 1.0e-6,
        "xc_functional": "PBE",
        "periodic": "XYZ",
        "cell_a": "15.49466",
        "cell_b": "15.49466",
        "cell_c": "15.49466",
        "coord_file": "structure.xyz",
        "coord_format": "XYZ",
        "o_basis_set": "DZVP-MOLOPT-SR-GTH",
        "o_potential": "GTH-PBE-q6",
        "h_basis_set": "DZVP-MOLOPT-SR-GTH",
        "h_potential": "GTH-PBE-q1",
        "restart_file": None,
        "restart_counters": True,
        "traj_freq": 1,
        "restart_freq": 50,
        "traj_format": "XYZ",
        "qs_extrapolation": "ASPC",
        "qs_extrapolation_order": 3,
        "optimizer": "BFGS",
        "max_geo_opt_iter": 200,
        "max_cell_opt_iter": 100,
        "max_force": 4.5e-4,
        "rms_force": 3.0e-4,
        "max_dr": 3.0e-3,
        "rms_dr": 2.0e-3,
        "keep_symmetry": "FALSE",
        "cell_opt_type": "DIRECT_CELL_OPT",
        "steps": 200,
        "timestep": 0.5,
        "temperature": 300.0,
        "thermostat_type": "CSVR",
        "thermostat_timecon": 200.0,
        "barostat_timecon": 500.0,
        "pressure_bar": 1.0,
    }

    if task == "energy":
        base.update({
            "project_name": "cp2k_energy",
            "coord_file": "last_frame.xyz",
        })
    elif task == "geo_opt":
        base.update({
            "project_name": "cp2k_geo_opt",
            "coord_file": "structure.xyz",
            "restart_freq": 5,
        })
    elif task == "cell_opt":
        base.update({
            "project_name": "cp2k_cell_opt",
            "coord_file": "structure.xyz",
            "restart_freq": 5,
        })
    elif task == "aimd_nvt":
        base.update({
            "project_name": "cp2k_aimd_nvt",
            "coord_file": "structure.xyz",
        })
    elif task == "aimd_nve":
        base.update({
            "project_name": "cp2k_aimd_nve",
            "coord_file": "structure.xyz",
        })
    elif task == "aimd_npt":
        base.update({
            "project_name": "cp2k_aimd_npt",
            "coord_file": "structure.xyz",
        })

    return base


def read_cif_to_xyz(cif_path: str | Path) -> tuple[str, list[str], dict]:
    """Read a CIF file and convert it to XYZ atom lines plus cell lengths."""
    content = Path(cif_path).read_text(encoding="utf-8")

    a = b = c = alpha = beta = gamma = None
    for raw in content.splitlines():
        line = raw.strip()
        if line.startswith("_cell_length_a"):
            a = float(line.split()[1])
        elif line.startswith("_cell_length_b"):
            b = float(line.split()[1])
        elif line.startswith("_cell_length_c"):
            c = float(line.split()[1])
        elif line.startswith("_cell_angle_alpha"):
            alpha = float(line.split()[1])
        elif line.startswith("_cell_angle_beta"):
            beta = float(line.split()[1])
        elif line.startswith("_cell_angle_gamma"):
            gamma = float(line.split()[1])

    if None in (a, b, c, alpha, beta, gamma):
        raise ValueError(f"Could not parse cell parameters from {cif_path}")

    alpha_r = math.radians(alpha)
    beta_r = math.radians(beta)
    gamma_r = math.radians(gamma)

    cos_alpha = math.cos(alpha_r)
    cos_beta = math.cos(beta_r)
    cos_gamma = math.cos(gamma_r)
    sin_gamma = math.sin(gamma_r)

    v1x = a
    v2x = b * cos_gamma
    v2y = b * sin_gamma
    v3x = c * cos_beta
    v3y = c * (cos_alpha - cos_beta * cos_gamma) / sin_gamma
    vol_factor = math.sqrt(
        1 - cos_alpha**2 - cos_beta**2 - cos_gamma**2
        + 2 * cos_alpha * cos_beta * cos_gamma
    )
    v3z = c * vol_factor / sin_gamma

    in_loop = False
    header_indices: dict[str, int] = {}
    atom_data: list[list[str]] = []
    lines = content.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("loop_"):
            in_loop = True
            header_indices = {}
            i += 1
            continue
        if in_loop and line.startswith("_atom_site_"):
            header_indices[line.split()[0]] = len(header_indices)
            i += 1
            continue
        if in_loop and header_indices and line and not line.startswith("#") and not line.startswith("_"):
            parts = line.split()
            if len(parts) >= len(header_indices):
                atom_data.append(parts)
            i += 1
            continue
        if in_loop and not line:
            in_loop = False
        i += 1

    if not atom_data:
        raise ValueError(f"No atom sites found in {cif_path}")

    type_idx = header_indices.get("_atom_site_type_symbol")
    fract_x_idx = header_indices.get("_atom_site_fract_x")
    fract_y_idx = header_indices.get("_atom_site_fract_y")
    fract_z_idx = header_indices.get("_atom_site_fract_z")
    if None in (type_idx, fract_x_idx, fract_y_idx, fract_z_idx):
        raise ValueError(f"Missing required CIF columns in {cif_path}")

    xyz_lines: list[str] = []
    element_counts: dict[str, int] = {}
    for parts in atom_data:
        element = re.sub(r"\d+$", "", parts[type_idx]) or parts[type_idx]
        fx = float(parts[fract_x_idx]) % 1.0
        fy = float(parts[fract_y_idx]) % 1.0
        fz = float(parts[fract_z_idx]) % 1.0
        x = fx * v1x + fy * v2x + fz * v3x
        y = fy * v2y + fz * v3y
        z = fz * v3z
        xyz_lines.append(f"{element:2s}  {x:12.6f}  {y:12.6f}  {z:12.6f}")
        element_counts[element] = element_counts.get(element, 0) + 1

    return f"{a} {b} {c}", xyz_lines, element_counts


def read_xyz_structure(xyz_path: str | Path) -> tuple[list[str], dict[str, int], str]:
    """Read the first frame of an XYZ file and return atom lines and elements."""
    path = Path(xyz_path)
    content = path.read_text(encoding="utf-8")
    lines = [line.rstrip() for line in content.splitlines()]
    if len(lines) < 2:
        raise ValueError(f"XYZ file is too short: {xyz_path}")

    try:
        natoms = int(lines[0].strip())
    except ValueError as exc:
        raise ValueError(f"Invalid XYZ atom count in {xyz_path}") from exc

    atom_lines = lines[2:2 + natoms]
    if len(atom_lines) != natoms:
        raise ValueError(f"XYZ frame is incomplete in {xyz_path}")

    counts: dict[str, int] = {}
    for atom_line in atom_lines:
        parts = atom_line.split()
        if len(parts) < 4:
            raise ValueError(f"Malformed XYZ atom line in {xyz_path}: {atom_line}")
        element = parts[0]
        counts[element] = counts.get(element, 0) + 1

    return atom_lines, counts, lines[1]


def write_xyz(natoms: int, comment: str, lines: list[str]) -> str:
    """Format atom lines as XYZ text."""
    return f"{natoms}\n{comment}\n" + "\n".join(lines) + "\n"


def extract_last_frame(xyz_trajectory: str) -> str:
    """Extract the last complete XYZ frame from a CP2K trajectory string."""
    frames = list(_iter_xyz_frames(xyz_trajectory))
    if not frames:
        raise ValueError("No frames found in trajectory")
    natoms, comment, atom_lines = frames[-1]
    return write_xyz(natoms, comment, atom_lines)


def generate_input(params: dict, calc_type: str) -> str:
    """Generate a CP2K input deck for a supported common task."""
    task = normalize_calc_type(calc_type)
    merged = cp2k_defaults(task)
    merged.update(params)
    _apply_cell_abc(merged)
    _apply_restart_defaults(merged, params)
    elements = _resolve_kind_elements(merged)
    if elements:
        merged["elements"] = elements

    builders = {
        "energy": _build_energy,
        "geo_opt": _build_geo_opt,
        "cell_opt": _build_cell_opt,
        "aimd_nvt": _build_aimd_nvt,
        "aimd_nve": _build_aimd_nve,
        "aimd_npt": _build_aimd_npt,
    }
    return builders[task](merged)


def _iter_xyz_frames(content: str) -> Iterable[tuple[int, str, list[str]]]:
    lines = content.splitlines()
    i = 0
    while i < len(lines):
        raw = lines[i].strip()
        if not raw:
            i += 1
            continue
        try:
            natoms = int(raw)
        except ValueError:
            i += 1
            continue
        if i + 1 >= len(lines):
            break
        comment = lines[i + 1].rstrip()
        atom_lines = lines[i + 2:i + 2 + natoms]
        if len(atom_lines) == natoms:
            yield natoms, comment, atom_lines
        i += 2 + natoms


def _apply_cell_abc(params: dict) -> None:
    cell_abc = params.get("cell_abc")
    if not cell_abc:
        return
    parts = str(cell_abc).split()
    if len(parts) >= 3:
        params["cell_a"] = parts[0]
        params["cell_b"] = parts[1]
        params["cell_c"] = parts[2]


def _apply_restart_defaults(merged: dict, original_params: dict) -> None:
    restart_file = merged.get("restart_file")
    if restart_file and "scf_guess" not in original_params:
        merged["scf_guess"] = "RESTART"


def _resolve_kind_elements(params: dict) -> list[str] | None:
    raw = params.get("elements")
    if isinstance(raw, dict):
        return sorted(str(key) for key in raw)
    if raw:
        return sorted({str(item) for item in raw})

    counts = params.get("element_counts")
    if isinstance(counts, dict) and counts:
        return sorted(str(key) for key in counts)

    structure_elements = params.get("structure_elements")
    if structure_elements:
        return sorted({str(item) for item in structure_elements})

    coord_path = params.get("coord_path")
    if coord_path:
        path = Path(str(coord_path))
        if path.is_file():
            coord_format = str(params.get("coord_format", path.suffix.lstrip("."))).upper()
            if coord_format == "CIF" or path.suffix.lower() == ".cif":
                _, _, inferred = read_cif_to_xyz(path)
                return sorted(inferred)
            atom_lines, counts, _ = read_xyz_structure(path)
            if atom_lines:
                return sorted(counts)

    coord_text = params.get("coord_text")
    if isinstance(coord_text, str) and coord_text.strip():
        try:
            frame = extract_last_frame(coord_text)
            _, counts, _ = read_xyz_structure_from_text(frame)
            return sorted(counts)
        except ValueError:
            return None

    return None


def read_xyz_structure_from_text(xyz_text: str) -> tuple[list[str], dict[str, int], str]:
    """Parse the first XYZ frame from in-memory text."""
    frames = list(_iter_xyz_frames(xyz_text))
    if not frames:
        raise ValueError("No XYZ frame found in provided text")
    natoms, comment, atom_lines = frames[0]
    counts: dict[str, int] = {}
    for atom_line in atom_lines[:natoms]:
        parts = atom_line.split()
        if len(parts) < 4:
            raise ValueError(f"Malformed XYZ atom line: {atom_line}")
        counts[parts[0]] = counts.get(parts[0], 0) + 1
    return atom_lines, counts, comment


def _build_global(project_name: str, run_type: str, print_level: str) -> str:
    return (
        "&GLOBAL\n"
        f"  PROJECT {project_name}\n"
        f"  RUN_TYPE {run_type}\n"
        f"  PRINT_LEVEL {print_level}\n"
        "&END GLOBAL\n"
    )


def _build_ext_restart(params: dict) -> str:
    restart_file = params.get("restart_file")
    if not restart_file:
        return ""
    lines = [
        "&EXT_RESTART",
        f"  RESTART_FILE_NAME {restart_file}",
        f"  RESTART_COUNTERS {'T' if params.get('restart_counters', True) else 'F'}",
        "&END EXT_RESTART",
    ]
    return "\n".join(lines) + "\n"


def _build_kind_blocks(params: dict) -> str:
    elements = params.get("elements")
    if not elements:
        return (
            "    &KIND O\n"
            f"      BASIS_SET {params['o_basis_set']}\n"
            f"      POTENTIAL {params['o_potential']}\n"
            "    &END KIND\n"
            "    &KIND H\n"
            f"      BASIS_SET {params['h_basis_set']}\n"
            f"      POTENTIAL {params['h_potential']}\n"
            "    &END KIND"
        )

    elem_params = params.get("element_params", {})
    blocks = []
    for element in sorted(set(elements)):
        spec = elem_params.get(element, DEFAULT_ELEMENT_PARAMS.get(element))
        if spec is None:
            raise ValueError(
                f"No basis/potential for element '{element}'. "
                "Provide it via element_params or extend DEFAULT_ELEMENT_PARAMS."
            )
        blocks.append(
            "    &KIND {element}\n"
            "      BASIS_SET {basis}\n"
            "      POTENTIAL {potential}\n"
            "    &END KIND".format(
                element=element,
                basis=spec["basis"],
                potential=spec["potential"],
            )
        )
    return "\n".join(blocks)


def _build_force_eval(params: dict) -> str:
    qs_lines = [f"      EPS_DEFAULT {params['qs_eps_default']}"]
    if params.get("qs_extrapolation"):
        qs_lines.append(f"      EXTRAPOLATION {params['qs_extrapolation']}")
        qs_lines.append(f"      EXTRAPOLATION_ORDER {params['qs_extrapolation_order']}")
    qs_block = "\n".join(qs_lines)

    return f"""&FORCE_EVAL
  METHOD QS
  &DFT
    BASIS_SET_FILE_NAME {params['basis_set_file']}
    POTENTIAL_FILE_NAME {params['potential_file']}
    CHARGE {params['charge']}
    MULTIPLICITY {params['multiplicity']}
    &QS
{qs_block}
    &END QS
    &MGRID
      CUTOFF {params['cutoff']}
      REL_CUTOFF {params['rel_cutoff']}
    &END MGRID
    &SCF
      MAX_SCF {params['max_scf']}
      EPS_SCF {params['eps_scf']}
      SCF_GUESS {params['scf_guess']}
      &OT ON
        MINIMIZER {params['ot_minimizer']}
        PRECONDITIONER {params['ot_preconditioner']}
      &END OT
      &OUTER_SCF
        MAX_SCF {params['outer_max_scf']}
        EPS_SCF {params['outer_eps_scf']}
      &END OUTER_SCF
      &PRINT
        &RESTART OFF
        &END RESTART
      &END PRINT
    &END SCF
    &XC
      &XC_FUNCTIONAL {params['xc_functional']}
      &END XC_FUNCTIONAL
    &END XC
  &END DFT
  &SUBSYS
    &CELL
      ABC {params['cell_a']} {params['cell_b']} {params['cell_c']}
      PERIODIC {params['periodic']}
    &END CELL
    &TOPOLOGY
      COORD_FILE_NAME {params['coord_file']}
      COORD_FILE_FORMAT {params.get('coord_format', 'XYZ')}
    &END TOPOLOGY
{_build_kind_blocks(params)}
  &END SUBSYS
&END FORCE_EVAL
"""


def _build_motion_print(each_label: str, params: dict, include_trajectory: bool) -> str:
    lines = ["  &PRINT"]
    if include_trajectory:
        lines.extend([
            "    &TRAJECTORY",
            f"      FORMAT {params['traj_format']}",
            "      &EACH",
            f"        {each_label} {params['traj_freq']}",
            "      &END EACH",
            "    &END TRAJECTORY",
        ])
    lines.extend([
        "    &RESTART",
        "      BACKUP_COPIES 1",
        "      &EACH",
        f"        {each_label} {params['restart_freq']}",
        "      &END EACH",
        "    &END RESTART",
        "  &END PRINT",
    ])
    return "\n".join(lines)


def _build_energy(params: dict) -> str:
    sections = [
        _build_global(params["project_name"], "ENERGY", params["print_level"]),
    ]
    ext_restart = _build_ext_restart(params)
    if ext_restart:
        sections.append(ext_restart)
    sections.append(_build_force_eval(params))
    return "\n".join(sections)


def _build_geo_opt(params: dict) -> str:
    motion = f"""&MOTION
  &GEO_OPT
    TYPE MINIMIZATION
    OPTIMIZER {params['optimizer']}
    MAX_ITER {params['max_geo_opt_iter']}
    MAX_FORCE {params['max_force']}
    RMS_FORCE {params['rms_force']}
    MAX_DR {params['max_dr']}
    RMS_DR {params['rms_dr']}
  &END GEO_OPT
{_build_motion_print('GEO_OPT', params, include_trajectory=True)}
&END MOTION
"""
    sections = [
        _build_global(params["project_name"], "GEO_OPT", params["print_level"]),
    ]
    ext_restart = _build_ext_restart(params)
    if ext_restart:
        sections.append(ext_restart)
    sections.extend([motion, _build_force_eval(params)])
    return "\n".join(sections)


def _build_cell_opt(params: dict) -> str:
    motion = f"""&MOTION
  &CELL_OPT
    TYPE {params['cell_opt_type']}
    OPTIMIZER {params['optimizer']}
    MAX_ITER {params['max_cell_opt_iter']}
    KEEP_SYMMETRY {params['keep_symmetry']}
    EXTERNAL_PRESSURE [bar] {params['pressure_bar']}
  &END CELL_OPT
{_build_motion_print('CELL_OPT', params, include_trajectory=True)}
&END MOTION
"""
    sections = [
        _build_global(params["project_name"], "CELL_OPT", params["print_level"]),
    ]
    ext_restart = _build_ext_restart(params)
    if ext_restart:
        sections.append(ext_restart)
    sections.extend([motion, _build_force_eval(params)])
    return "\n".join(sections)


def _build_aimd_nvt(params: dict) -> str:
    motion = f"""&MOTION
  &MD
    ENSEMBLE NVT
    STEPS {params['steps']}
    TIMESTEP {params['timestep']}
    TEMPERATURE {params['temperature']}
    &THERMOSTAT
      TYPE {params['thermostat_type']}
      &CSVR
        TIMECON {params['thermostat_timecon']}
      &END CSVR
    &END THERMOSTAT
  &END MD
{_build_motion_print('MD', params, include_trajectory=True)}
&END MOTION
"""
    sections = [
        _build_global(params["project_name"], "MD", params["print_level"]),
    ]
    ext_restart = _build_ext_restart(params)
    if ext_restart:
        sections.append(ext_restart)
    sections.extend([motion, _build_force_eval(params)])
    return "\n".join(sections)


def _build_aimd_nve(params: dict) -> str:
    motion = f"""&MOTION
  &MD
    ENSEMBLE NVE
    STEPS {params['steps']}
    TIMESTEP {params['timestep']}
  &END MD
{_build_motion_print('MD', params, include_trajectory=True)}
&END MOTION
"""
    sections = [
        _build_global(params["project_name"], "MD", params["print_level"]),
    ]
    ext_restart = _build_ext_restart(params)
    if ext_restart:
        sections.append(ext_restart)
    sections.extend([motion, _build_force_eval(params)])
    return "\n".join(sections)


def _build_aimd_npt(params: dict) -> str:
    motion = f"""&MOTION
  &MD
    ENSEMBLE NPT_I
    STEPS {params['steps']}
    TIMESTEP {params['timestep']}
    TEMPERATURE {params['temperature']}
    PRESSURE [bar] {params['pressure_bar']}
    &THERMOSTAT
      TYPE {params['thermostat_type']}
      &CSVR
        TIMECON {params['thermostat_timecon']}
      &END CSVR
    &END THERMOSTAT
    &BAROSTAT
      TIMECON {params['barostat_timecon']}
    &END BAROSTAT
  &END MD
{_build_motion_print('MD', params, include_trajectory=True)}
&END MOTION
"""
    sections = [
        _build_global(params["project_name"], "MD", params["print_level"]),
    ]
    ext_restart = _build_ext_restart(params)
    if ext_restart:
        sections.append(ext_restart)
    sections.extend([motion, _build_force_eval(params)])
    return "\n".join(sections)
