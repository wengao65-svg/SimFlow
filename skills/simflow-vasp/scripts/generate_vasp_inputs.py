#!/usr/bin/env python3
"""Generate complete VASP input set using pymatgen.

Creates INCAR, KPOINTS, POTCAR info, and optionally copies POSCAR.
Uses pymatgen.io.vasp for structured input generation.

NBANDS policy: ordinary calculations (relax, scf, static, bands, dos) do not
write NBANDS by default. Special calculations (optics, gw, etc.) get automatic
NBANDS. User-explicit NBANDS is validated against occupied_bands.
"""

import argparse
import json
import os
import sys
from pathlib import Path

# Add runtime to path for vasp_potcar/vasp_incar modules
SIMFLOW_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(SIMFLOW_ROOT / "runtime"))

try:
    from pymatgen.core import Structure
    from pymatgen.io.vasp import Incar, Kpoints
except ImportError:
    print(json.dumps({"status": "error", "message": "pymatgen not installed"}))
    sys.exit(1)

from lib.vasp_potcar import generate_potcar, validate_potcar, get_potcar_nelect
from lib.vasp_incar import apply_nbands_policy, get_explicit_user_nbands


def generate_incar(job_type: str, params: dict, structure: Structure = None,
                   potcar_path: str = None) -> Incar:
    """Generate pymatgen Incar object with appropriate defaults.

    NBANDS policy is applied after merging defaults with user params:
    - Ordinary calc types: NBANDS removed even if residual in params
    - Special calc types (optics, gw, etc.): NBANDS auto-calculated
    - User-explicit NBANDS: validated and preserved

    Args:
        job_type: VASP job type (scf, relax, vc-relax, md, bands, optics, etc.)
        params: User parameter overrides
        structure: pymatgen Structure (needed for NELECT/NBANDS calculation)
        potcar_path: Path to POTCAR (needed for ZVAL/NELECT extraction)
    """
    defaults = {
        "PREC": "Accurate",
        "ENCUT": 520,
        "EDIFF": 1e-6,
        "NELM": 200,
        "ALGO": "Normal",
        "ISMEAR": 0,
        "SIGMA": 0.05,
        "ISPIN": 1,
        "LWAVE": False,
        "LCHARG": False,
    }

    if job_type == "scf":
        defaults.update({"NSW": 0, "IBRION": -1})
    elif job_type == "relax":
        defaults.update({"NSW": 100, "IBRION": 2, "ISIF": 2, "EDIFFG": -0.01})
    elif job_type == "vc-relax":
        defaults.update({"NSW": 100, "IBRION": 2, "ISIF": 3, "EDIFFG": -0.01})
    elif job_type == "md":
        defaults.update({"NSW": 10000, "IBRION": 0, "POTIM": 1.0, "MDALGO": 2})

    # Merge user params FIRST
    defaults.update(params)

    # Apply NBANDS policy AFTER merging, so we can override/remove residual NBANDS
    if structure is not None:
        # Determine NELECT: prefer user-explicit, then POTCAR ZVAL
        nelect = params.get("NELECT")
        if nelect is None and potcar_path and Path(potcar_path).is_file():
            try:
                nelect = get_potcar_nelect(potcar_path, str(structure))
            except (ValueError, FileNotFoundError):
                pass

        if nelect is not None:
            nions = len(structure)
            user_nbands = get_explicit_user_nbands(params)
            ispin = int(params.get("ISPIN", defaults.get("ISPIN", 1)))
            total_magmom = params.get("MAGMOM") if ispin == 2 else None
            lnoncollinear = bool(params.get("LNONCOLLINEAR", False))

            apply_nbands_policy(
                incar=defaults,
                calc_type=job_type,
                nelect=float(nelect),
                nions=nions,
                user_nbands=user_nbands,
                ispin=ispin,
                total_magmom=total_magmom,
                lnoncollinear=lnoncollinear,
            )

    return Incar(defaults)


def generate_kpoints(structure: Structure, kppa: int = 1000, style: str = "Gamma") -> Kpoints:
    """Generate KPOINTS from structure using kpoint density."""
    kpts = Kpoints.automatic_density(structure, kppa)
    return kpts


def generate_vasp_inputs(poscar_path: str, job_type: str, output_dir: str,
                         params: dict = None, kppa: int = 1000,
                         potcar_root: str = None, use_vaspkit: bool = False) -> dict:
    """Generate complete VASP input set.

    Args:
        poscar_path: Input POSCAR file
        job_type: VASP job type (scf, relax, vc-relax, md, bands, optics, etc.)
        output_dir: Output directory
        params: INCAR parameter overrides
        kppa: K-points per reciprocal atom
        potcar_root: Path to pseudopotential library (default: from env)
        use_vaspkit: Use vaspkit for POTCAR generation

    Returns:
        Dict with status, files generated, and POTCAR generation info
    """
    structure = Structure.from_file(poscar_path)
    params = params or {}

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # POTCAR generation (before INCAR, so we can read ZVAL for NELECT)
    potcar_out = output_path / "POTCAR"
    potcar_result = generate_potcar(
        poscar_path=str(poscar_path),
        output_path=str(potcar_out),
        potcar_root=potcar_root,
        use_vaspkit=use_vaspkit,
    )

    files_generated = []
    potcar_path_for_incar = None

    if potcar_result["status"] == "success":
        potcar_path_for_incar = str(potcar_out)
        files_generated.append(str(potcar_out))
        validation = validate_potcar(str(poscar_path), str(potcar_out))
        potcar_result["validation"] = validation
    else:
        # Fallback: write POTCAR_info.json with generation instructions
        potcar_info = {
            "note": "POTCAR could not be generated automatically",
            "elements": [str(s) for s in structure.composition.elements],
            "generation": potcar_result,
        }
        (output_path / "POTCAR_info.json").write_text(json.dumps(potcar_info, indent=2))

    # INCAR (after POTCAR, so we can read ZVAL for NBANDS policy)
    incar = generate_incar(job_type, params, structure=structure,
                           potcar_path=potcar_path_for_incar)
    incar_path = output_path / "INCAR"
    incar.write_file(str(incar_path))
    files_generated.insert(0, str(incar_path))

    # KPOINTS
    kpoints = generate_kpoints(structure, kppa)
    kpoints_path = output_path / "KPOINTS"
    kpoints.write_file(str(kpoints_path))
    files_generated.insert(1, str(kpoints_path))

    # Copy POSCAR
    poscar_out = output_path / "POSCAR"
    structure.to(filename=str(poscar_out), fmt="poscar")
    files_generated.insert(2, str(poscar_out))

    return {
        "status": "success",
        "job_type": job_type,
        "output_dir": str(output_path),
        "files_generated": files_generated,
        "num_atoms": len(structure),
        "elements": [str(s) for s in structure.composition.elements],
        "kpoints_mesh": kpoints.kpts[0],
        "incar_params": dict(incar),
        "potcar": potcar_result,
    }


def main():
    parser = argparse.ArgumentParser(description="Generate VASP inputs using pymatgen")
    parser.add_argument("--poscar", required=True, help="Input POSCAR file")
    parser.add_argument("--job-type", required=True,
                        choices=["scf", "relax", "vc-relax", "md", "bands",
                                 "dos", "nscf", "optics", "dielectric", "eels",
                                 "gw", "rpa", "bse", "wannier"],
                        help="VASP job type")
    parser.add_argument("--output-dir", default="vasp_input", help="Output directory")
    parser.add_argument("--params", type=str, default="{}",
                        help="JSON string of INCAR parameter overrides")
    parser.add_argument("--kppa", type=int, default=1000,
                        help="K-points per reciprocal atom")
    parser.add_argument("--potcar-root", type=str, default=None,
                        help="Path to VASP pseudopotential library (overrides SIMFLOW_VASP_POTCAR_PATH)")
    parser.add_argument("--use-vaspkit", action="store_true",
                        help="Use vaspkit for POTCAR generation")
    args = parser.parse_args()

    try:
        params = json.loads(args.params)
        result = generate_vasp_inputs(args.poscar, args.job_type, args.output_dir,
                                       params, args.kppa,
                                       potcar_root=args.potcar_root,
                                       use_vaspkit=args.use_vaspkit)
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(json.dumps({"status": "error", "message": str(e)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
