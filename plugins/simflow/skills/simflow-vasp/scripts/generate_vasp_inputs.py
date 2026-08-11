#!/usr/bin/env python3
"""Generate complete VASP input set using pymatgen.

Creates INCAR, KPOINTS, POTCAR info, and optionally copies POSCAR.
Uses pymatgen.io.vasp for structured input generation.

NBANDS policy: ordinary calculations (relax, scf, static, bands, dos) do not
write NBANDS by default. Special calculations (optics, gw, etc.) get automatic
NBANDS. User-explicit NBANDS is validated against occupied_bands.

NCORE/NPAR policy: unknown hardware omits both and reports missing execution
context; confirmed CPU defaults to NPAR=4; GPU/OpenACC/offload omits both by
default; user-explicit values are preserved with warnings when needed.
"""

import argparse
import json
import os
import sys
from pathlib import Path

# Add runtime to path for vasp_potcar/vasp_incar modules
SIMFLOW_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(SIMFLOW_ROOT))
sys.path.insert(0, str(SIMFLOW_ROOT / "runtime"))

from runtime.simflow_core.result_contract import attach_simflow_result
from runtime.simflow_core.script_contracts import add_helper_recording_args, maybe_record_helper_run

try:
    from pymatgen.core import Structure
    from pymatgen.io.vasp import Incar, Kpoints
except ImportError:
    print(json.dumps({"status": "error", "message": "pymatgen not installed"}))
    sys.exit(1)

from runtime.simflow_helpers.engines.vasp_potcar import (
    generate_potcar,
    get_potcar_nelect,
    get_potcar_path,
    read_poscar_species,
)
from runtime.simflow_helpers.engines.vasp_incar import (
    apply_nbands_policy,
    apply_ncore_npar_policy,
    filter_vasp_incar_params,
    get_explicit_user_nbands,
)


def generate_incar(job_type: str, params: dict, structure: Structure = None,
                   potcar_path: str = None,
                   poscar_path: str = None,
                   return_policy_report: bool = False) -> Incar:
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
    params = params or {}
    incar_params = filter_vasp_incar_params(params)

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

    if job_type in {"scf", "static"}:
        defaults.update({"NSW": 0, "IBRION": -1})
    elif job_type == "relax":
        defaults.update({"NSW": 100, "IBRION": 2, "ISIF": 2, "EDIFFG": -0.01})
    elif job_type == "vc-relax":
        defaults.update({"NSW": 100, "IBRION": 2, "ISIF": 3, "EDIFFG": -0.01})
    elif job_type in {"md", "aimd"}:
        defaults.update({"NSW": 10000, "IBRION": 0, "POTIM": 1.0, "MDALGO": 2})
    elif job_type in {"bands", "band"}:
        defaults.update({"NSW": 0, "IBRION": -1, "ICHARG": 11, "LORBIT": 11})
    elif job_type == "dos":
        defaults.update({"NSW": 0, "IBRION": -1, "ICHARG": 11, "LORBIT": 11, "NEDOS": 2001})
    elif job_type in {"neb", "neb_basic"}:
        defaults.update({"NSW": 200, "IBRION": 3, "POTIM": 0.0, "IMAGES": incar_params.get("IMAGES", 1)})

    # Merge user params FIRST
    defaults.update(incar_params)

    # Apply NBANDS policy AFTER merging, so we can override/remove residual NBANDS
    if structure is not None:
        # Determine NELECT: prefer user-explicit, then POTCAR ZVAL
        nelect = params.get("NELECT")
        if nelect is None and potcar_path and poscar_path and Path(potcar_path).is_file():
            try:
                nelect = get_potcar_nelect(potcar_path, poscar_path)
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

    policy_report = {
        "ncore_npar": apply_ncore_npar_policy(defaults, params),
    }

    if return_policy_report:
        return Incar(defaults), policy_report
    return Incar(defaults)


def generate_kpoints(structure: Structure, kppa: int = 1000, style: str = "Gamma") -> Kpoints:
    """Generate KPOINTS from structure using kpoint density."""
    kpts = Kpoints.automatic_density(structure, kppa)
    return kpts


def generate_vasp_inputs(poscar_path: str, job_type: str, output_dir: str,
                         params: dict = None, kppa: int = 1000,
                         potcar_root: str = None, use_vaspkit: bool = False,
                         potcar_flavor: str = None,
                         potcar_setups: str | dict | None = None,
                         project_root: str = None) -> dict:
    """Generate complete VASP input set.

    Args:
        poscar_path: Input POSCAR file
        job_type: VASP job type (scf, relax, vc-relax, md, bands, optics, etc.)
        output_dir: Output directory
        params: INCAR parameter overrides
        kppa: K-points per reciprocal atom
        potcar_root: User-configured pseudopotential library root
        use_vaspkit: Compatibility-only VASPKIT toggle; never used for POTCAR
        potcar_flavor: POTCAR functional flavor
        potcar_setups: Fixed ASE-style profile or element suffix overrides
        project_root: Optional project boundary for restricted materialization

    Returns:
        Dict with status, files generated, and POTCAR generation info
    """
    structure = Structure.from_file(poscar_path)
    params = params or {}

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Write the normalized POSCAR first so POTCAR selection follows the exact
    # species order that VASP will consume.
    poscar_out = output_path / "POSCAR"
    structure.to(filename=str(poscar_out), fmt="poscar")
    files_generated = [str(poscar_out)]

    potcar_out = output_path / "POTCAR"
    potcar_path_for_incar = None
    try:
        elements = read_poscar_species(str(poscar_out))
    except Exception:
        elements = [str(s) for s in structure.composition.elements]

    configured_root = potcar_root or get_potcar_path()
    if configured_root and ".simflow" in output_path.resolve().parts:
        potcar_result = {
            "status": "metadata_only",
            "reason_code": "calculation_dir_required",
            "message": "Configured POTCAR materialization requires a calculation directory outside .simflow.",
            "elements": elements,
            "resolved_datasets": [],
            "restricted": True,
            "content_materialized": False,
            "content_included": False,
            "output_name": "POTCAR",
        }
    else:
        potcar_result = generate_potcar(
            str(poscar_out),
            str(potcar_out),
            potcar_root=potcar_root,
            flavor=potcar_flavor,
            setups=potcar_setups,
            use_vaspkit=use_vaspkit,
            project_root=project_root,
        )

    if potcar_result["status"] in {"materialized", "existing"} and potcar_out.is_file():
        potcar_path_for_incar = str(potcar_out)
    else:
        potcar_info = {
            "note": "Restricted POTCAR content is not included in this metadata file.",
            "elements": elements,
            "generation": potcar_result,
            "allowed_action": "Configure a licensed local POTCAR library and a controlled calculation directory before real execution.",
        }
        (output_path / "POTCAR_info.json").write_text(json.dumps(potcar_info, indent=2))
        files_generated.append(str(output_path / "POTCAR_info.json"))

    if potcar_result["status"] in {"error", "needs_inputs"}:
        result = {
            "status": potcar_result["status"],
            "reason_code": potcar_result.get("reason_code"),
            "message": potcar_result.get("message"),
            "job_type": job_type,
            "output_dir": str(output_path),
            "files_generated": files_generated,
            "num_atoms": len(structure),
            "elements": [str(s) for s in structure.composition.elements],
            "potcar": potcar_result,
        }
        return attach_simflow_result(
            result,
            role="helper",
            activity="vasp_generate_inputs",
            legacy_status=result["status"],
            stage="computation",
            state_effect="none",
        )

    # INCAR (after POTCAR, so we can read ZVAL for NBANDS policy)
    incar, incar_policy = generate_incar(
        job_type,
        params,
        structure=structure,
        potcar_path=potcar_path_for_incar,
        poscar_path=str(poscar_out),
        return_policy_report=True,
    )
    incar_path = output_path / "INCAR"
    incar.write_file(str(incar_path))
    files_generated.insert(0, str(incar_path))

    # KPOINTS
    kpoints = generate_kpoints(structure, kppa)
    kpoints_path = output_path / "KPOINTS"
    kpoints.write_file(str(kpoints_path))
    files_generated.insert(1, str(kpoints_path))

    result = {
        "status": "success",
        "job_type": job_type,
        "output_dir": str(output_path),
        "files_generated": files_generated,
        "num_atoms": len(structure),
        "elements": [str(s) for s in structure.composition.elements],
        "kpoints_mesh": kpoints.kpts[0],
        "incar_params": dict(incar),
        "incar_policy": incar_policy,
        "potcar": potcar_result,
    }
    return attach_simflow_result(
        result,
        role="helper",
        activity="vasp_generate_inputs",
        legacy_status=result["status"],
        stage="computation",
        state_effect="none",
    )


def main():
    parser = argparse.ArgumentParser(description="Generate VASP inputs using pymatgen")
    parser.add_argument("--poscar", required=True, help="Input POSCAR file")
    parser.add_argument("--job-type", required=True,
                        choices=["scf", "static", "relax", "vc-relax", "md", "aimd",
                                 "bands", "band", "dos", "nscf", "neb", "neb_basic",
                                 "optics", "dielectric", "eels",
                                 "gw", "rpa", "bse", "wannier"],
                        help="VASP job type")
    parser.add_argument("--output-dir", default="vasp_input", help="Output directory")
    parser.add_argument("--params", type=str, default="{}",
                        help="JSON string of INCAR parameter overrides")
    parser.add_argument("--kppa", type=int, default=1000,
                        help="K-points per reciprocal atom")
    parser.add_argument("--potcar-root", type=str, default=None,
                        help="Licensed local POTCAR library root; path is redacted from helper records")
    parser.add_argument("--potcar-flavor", type=str, default=None,
                        help="POTCAR functional flavor; defaults to SIMFLOW_VASP_POTCAR_FLAVOR or PBE")
    parser.add_argument("--potcar-setups", type=str, default=None,
                        help="minimal, recommended, gw, or a JSON object with base and element suffix overrides")
    parser.add_argument("--use-vaspkit", action="store_true",
                        help="Compatibility-only flag; SimFlow never delegates POTCAR materialization to VASPKIT")
    add_helper_recording_args(parser, default_stage="computation")
    args = parser.parse_args()

    try:
        params = json.loads(args.params)
        potcar_setups = args.potcar_setups
        if potcar_setups and potcar_setups.lstrip().startswith("{"):
            potcar_setups = json.loads(potcar_setups)
        result = generate_vasp_inputs(args.poscar, args.job_type, args.output_dir,
                                       params, args.kppa,
                                       potcar_root=args.potcar_root,
                                       use_vaspkit=args.use_vaspkit,
                                       potcar_flavor=args.potcar_flavor,
                                       potcar_setups=potcar_setups,
                                       project_root=args.project_root)
        result = maybe_record_helper_run(
            args=args,
            result=result,
            script_path=Path(__file__).resolve(),
            helper_name="vasp_generate_inputs",
            software="vasp",
            input_paths=[args.poscar],
            output_paths=result.get("files_generated", []),
            sensitive_cli_options=["--potcar-root"],
            sensitive_json_cli_options={
                "--params": [
                    "potcar_root",
                    "potcar_path",
                    "SIMFLOW_VASP_POTCAR_PATH",
                    "VASP_POTCAR_PATH",
                    "POTCAR_ROOT",
                    "POTCAR_PATH",
                    "POTPAW",
                    "POTPAW_PBE",
                    "POTPAW_LDA",
                ],
            },
        )
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(json.dumps({"status": "error", "message": str(e)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
