#!/usr/bin/env python3
"""Generate complete VASP input set using pymatgen.

Creates INCAR, KPOINTS, POTCAR info, and optionally copies POSCAR.
Uses pymatgen.io.vasp for structured input generation.
"""

import argparse
import json
import sys
from pathlib import Path

try:
    from pymatgen.core import Structure
    from pymatgen.io.vasp import Incar, Kpoints
except ImportError:
    print(json.dumps({"status": "error", "message": "pymatgen not installed"}))
    sys.exit(1)


def generate_incar(job_type: str, params: dict) -> Incar:
    """Generate pymatgen Incar object with appropriate defaults."""
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

    defaults.update(params)
    return Incar(defaults)


def generate_kpoints(structure: Structure, kppa: int = 1000, style: str = "Gamma") -> Kpoints:
    """Generate KPOINTS from structure using kpoint density."""
    kpts = Kpoints.automatic_density(structure, kppa)
    return kpts


def generate_vasp_inputs(poscar_path: str, job_type: str, output_dir: str,
                         params: dict = None, kppa: int = 1000) -> dict:
    """Generate complete VASP input set."""
    structure = Structure.from_file(poscar_path)
    params = params or {}

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # INCAR
    incar = generate_incar(job_type, params)
    incar_path = output_path / "INCAR"
    incar.write_file(str(incar_path))

    # KPOINTS
    kpoints = generate_kpoints(structure, kppa)
    kpoints_path = output_path / "KPOINTS"
    kpoints.write_file(str(kpoints_path))

    # Copy POSCAR
    poscar_out = output_path / "POSCAR"
    structure.to(filename=str(poscar_out), fmt="poscar")

    # POTCAR info (actual POTCAR requires VASP pseudopotential library)
    potcar_info = {
        "note": "POTCAR must be generated from VASP pseudopotential library",
        "elements": [str(s) for s in structure.composition.elements],
    }
    (output_path / "POTCAR_info.json").write_text(json.dumps(potcar_info, indent=2))

    return {
        "status": "success",
        "job_type": job_type,
        "output_dir": str(output_path),
        "files_generated": [str(incar_path), str(kpoints_path), str(poscar_out)],
        "num_atoms": len(structure),
        "elements": [str(s) for s in structure.composition.elements],
        "kpoints_mesh": kpoints.kpts[0],
        "incar_params": dict(incar),
    }


def main():
    parser = argparse.ArgumentParser(description="Generate VASP inputs using pymatgen")
    parser.add_argument("--poscar", required=True, help="Input POSCAR file")
    parser.add_argument("--job-type", required=True, choices=["scf", "relax", "vc-relax", "md"],
                        help="VASP job type")
    parser.add_argument("--output-dir", default="vasp_input", help="Output directory")
    parser.add_argument("--params", type=str, default="{}",
                        help="JSON string of INCAR parameter overrides")
    parser.add_argument("--kppa", type=int, default=1000,
                        help="K-points per reciprocal atom")
    args = parser.parse_args()

    try:
        params = json.loads(args.params)
        result = generate_vasp_inputs(args.poscar, args.job_type, args.output_dir,
                                       params, args.kppa)
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(json.dumps({"status": "error", "message": str(e)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
