"""CP2K input generation and structure handling.

Provides functions for generating CP2K input files (AIMD NVT, DFT single point),
reading CIF structures, and extracting trajectory frames. Operates on dicts
(no file I/O for parameter logic).

CP2K input format reference: https://manual.cp2k.org/
Key sections: GLOBAL, FORCE_EVAL, DFT, MGRID, SCF, XC, MOTION/MD, THERMOSTAT
"""

import math
import re
from pathlib import Path


# Element symbols for Z → symbol mapping
_ELEMENTS = [
    "", "H", "He", "Li", "Be", "B", "C", "N", "O", "F", "Ne",
    "Na", "Mg", "Al", "Si", "P", "S", "Cl", "Ar", "K", "Ca",
]

# Default basis set and potential for common elements (GTH-PBE / DZVP-MOLOPT-SR-GTH)
DEFAULT_ELEMENT_PARAMS = {
    "H":  {"basis": "DZVP-MOLOPT-SR-GTH", "potential": "GTH-PBE-q1"},
    "He": {"basis": "DZVP-MOLOPT-SR-GTH", "potential": "GTH-PBE-q2"},
    "Li": {"basis": "DZVP-MOLOPT-SR-GTH", "potential": "GTH-PBE-q3"},
    "Be": {"basis": "DZVP-MOLOPT-SR-GTH", "potential": "GTH-PBE-q4"},
    "B":  {"basis": "DZVP-MOLOPT-SR-GTH", "potential": "GTH-PBE-q3"},
    "C":  {"basis": "DZVP-MOLOPT-SR-GTH", "potential": "GTH-PBE-q4"},
    "N":  {"basis": "DZVP-MOLOPT-SR-GTH", "potential": "GTH-PBE-q5"},
    "O":  {"basis": "DZVP-MOLOPT-SR-GTH", "potential": "GTH-PBE-q6"},
    "F":  {"basis": "DZVP-MOLOPT-SR-GTH", "potential": "GTH-PBE-q7"},
    "Ne": {"basis": "DZVP-MOLOPT-SR-GTH", "potential": "GTH-PBE-q8"},
    "Na": {"basis": "DZVP-MOLOPT-SR-GTH", "potential": "GTH-PBE-q9"},
    "Mg": {"basis": "DZVP-MOLOPT-SR-GTH", "potential": "GTH-PBE-q2"},
    "Al": {"basis": "DZVP-MOLOPT-SR-GTH", "potential": "GTH-PBE-q3"},
    "Si": {"basis": "DZVP-MOLOPT-SR-GTH", "potential": "GTH-PBE-q4"},
    "P":  {"basis": "DZVP-MOLOPT-SR-GTH", "potential": "GTH-PBE-q5"},
    "S":  {"basis": "DZVP-MOLOPT-SR-GTH", "potential": "GTH-PBE-q6"},
    "Cl": {"basis": "DZVP-MOLOPT-SR-GTH", "potential": "GTH-PBE-q7"},
    "Ar": {"basis": "DZVP-MOLOPT-SR-GTH", "potential": "GTH-PBE-q8"},
    "K":  {"basis": "DZVP-MOLOPT-SR-GTH", "potential": "GTH-PBE-q9"},
    "Ca": {"basis": "DZVP-MOLOPT-SR-GTH", "potential": "GTH-PBE-q10"},
}


def cp2k_defaults(calc_type: str = "aimd_nvt") -> dict:
    """Return default CP2K parameters for the given calculation type.

    Args:
        calc_type: "aimd_nvt" or "energy"

    Returns:
        Dict of parameter name → default value
    """
    base = {
        "print_level": "LOW",
        "basis_set_file": "BASIS_MOLOPT",
        "potential_file": "POTENTIAL",
        "charge": 0,
        "multiplicity": 1,
        "cutoff": 400,          # Ry
        "rel_cutoff": 50,       # Ry
        "qs_eps_default": 1.0E-8,
        "max_scf": 50,
        "eps_scf": 1.0E-6,
        "scf_guess": "ATOMIC",
        "ot_minimizer": "DIIS",
        "ot_preconditioner": "FULL_SINGLE_INVERSE",
        "outer_max_scf": 20,
        "outer_eps_scf": 1.0E-6,
        "xc_functional": "PBE",
        "o_basis_set": "DZVP-MOLOPT-SR-GTH",
        "o_potential": "GTH-PBE-q6",
        "h_basis_set": "DZVP-MOLOPT-SR-GTH",
        "h_potential": "GTH-PBE-q1",
        "periodic": "XYZ",
        "cell_a": "15.49466",
        "cell_b": "15.49466",
        "cell_c": "15.49466",
    }

    if calc_type == "aimd_nvt":
        base.update({
            "project_name": "H2O_aimd_nvt",
            "steps": 200,
            "timestep": 0.5,        # fs
            "temperature": 300.0,    # K
            "thermostat_type": "CSVR",
            "thermostat_timecon": 200.0,  # fs
            "traj_freq": 1,
            "traj_format": "XYZ",    # or "EXTXYZ" for CP2K 2026+
            "restart_freq": 200,
            "qs_extrapolation": "ASPC",
            "qs_extrapolation_order": 3,
            "coord_file": "structure.xyz",
        })
    elif calc_type == "energy":
        base.update({
            "project_name": "H2O_energy",
            "coord_file": "last_frame.xyz",
        })
    else:
        raise ValueError(f"Unknown calc_type: {calc_type}. Use 'aimd_nvt' or 'energy'.")

    return base


def read_cif_to_xyz(cif_path: str) -> tuple[str, list[str], dict]:
    """Read a CIF file and convert to XYZ format with cell parameters.

    Handles fractional → Cartesian conversion using cell parameters.
    Supports CIF files with _atom_site_fract_x/y/z and _atom_site_type_symbol.

    Args:
        cif_path: Path to CIF file

    Returns:
        (cell_abc, xyz_lines, element_counts)
        cell_abc: "a b c" string in Angstrom
        xyz_lines: list of "Element x y z" lines (XYZ format)
        element_counts: dict of {element: count}
    """
    content = Path(cif_path).read_text()

    # Parse cell parameters
    a = b = c = alpha = beta = gamma = None
    for line in content.split("\n"):
        line = line.strip()
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

    # Build fractional → Cartesian transformation matrix
    # Using standard crystallographic convention
    alpha_r = math.radians(alpha)
    beta_r = math.radians(beta)
    gamma_r = math.radians(gamma)

    cos_alpha = math.cos(alpha_r)
    cos_beta = math.cos(beta_r)
    cos_gamma = math.cos(gamma_r)
    sin_gamma = math.sin(gamma_r)

    # Transformation matrix (column vectors)
    # v1 = (a, 0, 0)
    # v2 = (b*cos_gamma, b*sin_gamma, 0)
    # v3 = (c*cos_beta, c*(cos_alpha - cos_beta*cos_gamma)/sin_gamma, c*V_factor)
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

    # Parse atom sites
    in_loop = False
    header_indices = {}
    atom_data = []

    lines = content.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i].strip()

        if line.startswith("loop_"):
            in_loop = True
            header_indices = {}
            i += 1
            continue

        if in_loop and line.startswith("_atom_site_"):
            col_name = line.split()[0]
            header_indices[col_name] = len(header_indices)
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

    # Find column indices
    type_idx = header_indices.get("_atom_site_type_symbol")
    fract_x_idx = header_indices.get("_atom_site_fract_x")
    fract_y_idx = header_indices.get("_atom_site_fract_y")
    fract_z_idx = header_indices.get("_atom_site_fract_z")

    if None in (type_idx, fract_x_idx, fract_y_idx, fract_z_idx):
        raise ValueError(f"Missing required CIF columns in {cif_path}")

    # Convert fractional to Cartesian
    xyz_lines = []
    element_counts = {}

    for parts in atom_data:
        element = parts[type_idx]
        # Strip trailing digits from element label (e.g., "O1" → "O")
        element_clean = re.sub(r"\d+$", "", element)
        if not element_clean:
            element_clean = element

        fx = float(parts[fract_x_idx])
        fy = float(parts[fract_y_idx])
        fz = float(parts[fract_z_idx])

        # Wrap to [0, 1) for periodic systems
        fx = fx % 1.0
        fy = fy % 1.0
        fz = fz % 1.0

        # Fractional → Cartesian
        x = fx * v1x + fy * v2x + fz * v3x
        y = fy * v2y + fz * v3y
        z = fz * v3z

        xyz_lines.append(f"{element_clean:2s}  {x:12.6f}  {y:12.6f}  {z:12.6f}")
        element_counts[element_clean] = element_counts.get(element_clean, 0) + 1

    cell_abc = f"{a} {b} {c}"
    return cell_abc, xyz_lines, element_counts


def write_xyz(natoms: int, comment: str, lines: list[str]) -> str:
    """Format an XYZ block.

    Args:
        natoms: Number of atoms
        comment: Comment line
        lines: Atom lines ("Element x y z")

    Returns:
        XYZ format string
    """
    return f"{natoms}\n{comment}\n" + "\n".join(lines) + "\n"


def extract_last_frame(xyz_trajectory: str) -> str:
    """Extract the last frame from a CP2K trajectory XYZ file.

    CP2K trajectory format:
        natoms
        i = STEP, time = TIME_FS, E = ENERGY
        Element  x  y  z
        ...

    Args:
        xyz_trajectory: Full trajectory content

    Returns:
        Last frame as XYZ string
    """
    frames = []
    lines = xyz_trajectory.strip().split("\n")
    i = 0

    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue

        # Try to parse natoms
        try:
            natoms = int(line)
        except ValueError:
            i += 1
            continue

        # Next line is comment
        if i + 1 >= len(lines):
            break
        comment = lines[i + 1]

        # Next natoms lines are atoms
        atom_lines = []
        for j in range(i + 2, min(i + 2 + natoms, len(lines))):
            atom_lines.append(lines[j])

        if len(atom_lines) == natoms:
            frames.append(write_xyz(natoms, comment, atom_lines))

        i += 2 + natoms

    if not frames:
        raise ValueError("No frames found in trajectory")

    return frames[-1]


def generate_input(params: dict, calc_type: str) -> str:
    """Generate CP2K input text from parameters.

    Args:
        params: User parameters (merged with defaults)
        calc_type: "aimd_nvt" or "energy"

    Returns:
        CP2K input file content
    """
    defaults = cp2k_defaults(calc_type)
    defaults.update(params)

    p = defaults

    if calc_type == "aimd_nvt":
        return _build_aimd_nvt(p)
    elif calc_type == "energy":
        return _build_energy(p)
    else:
        raise ValueError(f"Unknown calc_type: {calc_type}")


def _build_kind_blocks(p: dict) -> str:
    """Generate KIND blocks for all elements.

    Uses 'elements' list from params if available, otherwise falls back
    to legacy o_basis_set/h_basis_set parameters for O and H only.
    """
    elements = p.get("elements")
    if elements:
        # Dynamic KIND blocks from element list
        blocks = []
        elem_params = p.get("element_params", {})
        for elem in sorted(set(elements)):
            params = elem_params.get(elem, DEFAULT_ELEMENT_PARAMS.get(elem))
            if params is None:
                raise ValueError(
                    f"No basis/potential for element '{elem}'. "
                    f"Provide via element_params or add to DEFAULT_ELEMENT_PARAMS."
                )
            blocks.append(
                f"    &KIND {elem}\n"
                f"      BASIS_SET {params['basis']}\n"
                f"      POTENTIAL {params['potential']}\n"
                f"    &END KIND"
            )
        return "\n".join(blocks)
    else:
        # Legacy mode: hardcoded O/H
        return (
            f"    &KIND O\n"
            f"      BASIS_SET {p['o_basis_set']}\n"
            f"      POTENTIAL {p['o_potential']}\n"
            f"    &END KIND\n"
            f"    &KIND H\n"
            f"      BASIS_SET {p['h_basis_set']}\n"
            f"      POTENTIAL {p['h_potential']}\n"
            f"    &END KIND"
        )


def _build_aimd_nvt(p: dict) -> str:
    """Build AIMD NVT input text."""
    return f"""&GLOBAL
  PROJECT {p['project_name']}
  RUN_TYPE MD
  PRINT_LEVEL {p['print_level']}
&END GLOBAL

&MOTION
  &MD
    ENSEMBLE NVT
    STEPS {p['steps']}
    TIMESTEP {p['timestep']}
    TEMPERATURE {p['temperature']}
    &THERMOSTAT
      TYPE {p['thermostat_type']}
      &CSVR
        TIMECON {p['thermostat_timecon']}
      &END CSVR
    &END THERMOSTAT
  &END MD
  &PRINT
    &TRAJECTORY
      FORMAT {p['traj_format']}
      &EACH
        MD {p['traj_freq']}
      &END EACH
    &END TRAJECTORY
    &VELOCITIES OFF
    &END VELOCITIES
    &RESTART
      &EACH
        MD {p['restart_freq']}
      &END EACH
    &END RESTART
    &RESTART_HISTORY OFF
    &END RESTART_HISTORY
  &END PRINT
&END MOTION

&FORCE_EVAL
  METHOD QS
  &DFT
    BASIS_SET_FILE_NAME {p['basis_set_file']}
    POTENTIAL_FILE_NAME {p['potential_file']}
    CHARGE {p['charge']}
    MULTIPLICITY {p['multiplicity']}
    &QS
      EPS_DEFAULT {p['qs_eps_default']}
      EXTRAPOLATION {p['qs_extrapolation']}
      EXTRAPOLATION_ORDER {p['qs_extrapolation_order']}
    &END QS
    &MGRID
      CUTOFF {p['cutoff']}
      REL_CUTOFF {p['rel_cutoff']}
    &END MGRID
    &SCF
      MAX_SCF {p['max_scf']}
      EPS_SCF {p['eps_scf']}
      SCF_GUESS {p['scf_guess']}
      &OT ON
        MINIMIZER {p['ot_minimizer']}
        PRECONDITIONER {p['ot_preconditioner']}
      &END OT
      &OUTER_SCF
        MAX_SCF {p['outer_max_scf']}
        EPS_SCF {p['outer_eps_scf']}
      &END OUTER_SCF
      &PRINT
        &RESTART OFF
        &END RESTART
      &END PRINT
    &END SCF
    &XC
      &XC_FUNCTIONAL {p['xc_functional']}
      &END XC_FUNCTIONAL
    &END XC
  &END DFT
  &SUBSYS
    &CELL
      ABC {p['cell_a']} {p['cell_b']} {p['cell_c']}
      PERIODIC {p['periodic']}
    &END CELL
    &TOPOLOGY
      COORD_FILE_NAME {p['coord_file']}
      COORD_FILE_FORMAT {p.get('coord_format', 'XYZ')}
    &END TOPOLOGY
{_build_kind_blocks(p)}
  &END SUBSYS
&END FORCE_EVAL
"""


def _build_energy(p: dict) -> str:
    """Build DFT single-point energy input text."""
    return f"""&GLOBAL
  PROJECT {p['project_name']}
  RUN_TYPE ENERGY
  PRINT_LEVEL {p['print_level']}
&END GLOBAL

&FORCE_EVAL
  METHOD QS
  &DFT
    BASIS_SET_FILE_NAME {p['basis_set_file']}
    POTENTIAL_FILE_NAME {p['potential_file']}
    CHARGE {p['charge']}
    MULTIPLICITY {p['multiplicity']}
    &QS
      EPS_DEFAULT {p['qs_eps_default']}
    &END QS
    &MGRID
      CUTOFF {p['cutoff']}
      REL_CUTOFF {p['rel_cutoff']}
    &END MGRID
    &SCF
      MAX_SCF {p['max_scf']}
      EPS_SCF {p['eps_scf']}
      SCF_GUESS {p['scf_guess']}
      &OT ON
        MINIMIZER {p['ot_minimizer']}
        PRECONDITIONER {p['ot_preconditioner']}
      &END OT
      &OUTER_SCF
        MAX_SCF {p['outer_max_scf']}
        EPS_SCF {p['outer_eps_scf']}
      &END OUTER_SCF
      &PRINT
        &RESTART OFF
        &END RESTART
      &END PRINT
    &END SCF
    &XC
      &XC_FUNCTIONAL {p['xc_functional']}
      &END XC_FUNCTIONAL
    &END XC
  &END DFT
  &SUBSYS
    &CELL
      ABC {p['cell_a']} {p['cell_b']} {p['cell_c']}
      PERIODIC {p['periodic']}
    &END CELL
    &TOPOLOGY
      COORD_FILE_NAME {p['coord_file']}
      COORD_FILE_FORMAT {p.get('coord_format', 'XYZ')}
    &END TOPOLOGY
{_build_kind_blocks(p)}
  &END SUBSYS
&END FORCE_EVAL
"""
