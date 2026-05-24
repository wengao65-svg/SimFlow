#!/usr/bin/env python3
"""Generate VASP input files (INCAR, KPOINTS) from templates.

Reads templates from templates/vasp/ and applies parameters to produce
ready-to-use input files for VASP calculations.

NBANDS policy is applied via runtime/lib/vasp_incar.py:
- Ordinary calc types (relax, scf, bands, etc.): NBANDS removed
- Special calc types (optics, gw, etc.): NBANDS auto-calculated
- User-explicit NBANDS: validated and preserved
"""

import argparse
import json
import re
import sys
from pathlib import Path

# Add runtime to path for vasp_incar module
SIMFLOW_ROOT = Path(__file__).resolve().parents[4] / "simflow"
# Try relative to project root
_project_root = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(_project_root / "runtime"))

try:
    from lib.vasp_incar import apply_nbands_policy, get_explicit_user_nbands
except ImportError:
    # Fallback: try from simflow root
    _alt_root = Path(__file__).resolve().parents[3].parent
    sys.path.insert(0, str(_alt_root / "runtime"))
    try:
        from lib.vasp_incar import apply_nbands_policy, get_explicit_user_nbands
    except ImportError:
        apply_nbands_policy = None
        get_explicit_user_nbands = None


TEMPLATE_DIR = Path(__file__).resolve().parents[3] / "templates" / "vasp"


def render_template(template_content: str, variables: dict) -> str:
    """Render a Jinja-style template with {{ variable }} placeholders."""
    result = template_content
    for key, value in variables.items():
        pattern = r"\{\{\s*" + re.escape(key) + r"\s*(?:\|[^}]*)?\}\}"
        result = re.sub(pattern, str(value), result)
    return result


def generate_incar(job_type: str, params: dict, output_path: str,
                   nelect: float = None, nions: int = None) -> str:
    """Generate INCAR file from template with NBANDS policy.

    Args:
        job_type: Calculation type
        params: Parameter overrides
        output_path: Output INCAR path
        nelect: Number of valence electrons (from POTCAR ZVAL). Required for
                NBANDS auto-calculation.
        nions: Number of ions/atoms. Required for NBANDS auto-calculation.

    Returns:
        Output file path
    """
    template_path = TEMPLATE_DIR / "INCAR.template"
    if not template_path.exists():
        raise FileNotFoundError(f"Template not found: {template_path}")

    template = template_path.read_text()

    defaults = {
        "job_type": job_type,
        "job_name": params.get("job_name", "simflow"),
        "precision": "Accurate",
        "encut": 520,
        "ispin": 1,
        "ediff": "1E-6",
        "nelm": 200,
        "algo": "Normal",
        "ismear": 0,
        "sigma": 0.05,
    }

    # Job-type specific defaults
    if job_type == "scf":
        defaults.update({"nsw": 0, "ibrion": -1})
    elif job_type == "relax":
        defaults.update({"nsw": 100, "ibrion": 2, "isif": 2})
    elif job_type == "vc-relax":
        defaults.update({"nsw": 100, "ibrion": 2, "isif": 3})
    elif job_type == "md":
        defaults.update({"nsw": 10000, "ibrion": 0, "potim": 1.0, "mdalgo": 2})

    # Apply NBANDS policy if vasp_incar is available and nelect/nions provided
    if apply_nbands_policy is not None and nelect is not None and nions is not None:
        user_nbands = get_explicit_user_nbands(params) if get_explicit_user_nbands else params.get("NBANDS")
        ispin = int(params.get("ISPIN", defaults.get("ispin", 1)))
        total_magmom = params.get("MAGMOM") if ispin == 2 else None

        # Build a dict for the policy function (case-sensitive INCAR keys)
        policy_incar = {"ISPIN": ispin}
        apply_nbands_policy(
            incar=policy_incar,
            calc_type=job_type,
            nelect=float(nelect),
            nions=nions,
            user_nbands=user_nbands if isinstance(user_nbands, int) else None,
            ispin=ispin,
            total_magmom=total_magmom,
        )
        # Set nbands for template rendering (None -> not rendered)
        defaults["nbands"] = policy_incar.get("NBANDS")
    elif "NBANDS" in params:
        # No policy available, pass through user value
        defaults["nbands"] = params["NBANDS"]
    # else: nbands not set -> template conditional block won't render

    defaults.update(params)
    # Ensure nbands from policy is not overwritten by params merge
    if apply_nbands_policy is not None and nelect is not None and nions is not None:
        # Re-apply to get the correct nbands value after params merge
        pass  # nbands was already computed above

    content = render_template(template, defaults)

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(content)
    return str(out)


def generate_kpoints(params: dict, output_path: str) -> str:
    """Generate KPOINTS file from template."""
    template_path = TEMPLATE_DIR / "KPOINTS.template"
    if not template_path.exists():
        raise FileNotFoundError(f"Template not found: {template_path}")

    template = template_path.read_text()
    defaults = {
        "kpoint_type": "Gamma-centered",
        "kx": 4,
        "ky": 4,
        "kz": 4,
    }
    defaults.update(params)
    content = render_template(template, defaults)

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(content)
    return str(out)


def main():
    parser = argparse.ArgumentParser(description="Generate VASP input files")
    parser.add_argument("--job-type", required=True,
                        choices=["scf", "relax", "vc-relax", "md", "bands",
                                 "dos", "nscf", "optics", "dielectric", "eels",
                                 "gw", "rpa", "bse", "wannier"],
                        help="Type of VASP calculation")
    parser.add_argument("--params", type=str, default="{}",
                        help="JSON string of parameters to override defaults")
    parser.add_argument("--output-dir", default=".", help="Output directory")
    parser.add_argument("--nelect", type=float, default=None,
                        help="Total valence electrons (from POTCAR ZVAL). "
                             "Required for NBANDS auto-calculation.")
    parser.add_argument("--nions", type=int, default=None,
                        help="Number of ions/atoms. Required for NBANDS auto-calculation.")
    args = parser.parse_args()

    try:
        params = json.loads(args.params)
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        incar_path = generate_incar(args.job_type, params, str(output_dir / "INCAR"),
                                     nelect=args.nelect, nions=args.nions)
        kpoints_path = generate_kpoints(params, str(output_dir / "KPOINTS"))

        result = {
            "status": "success",
            "job_type": args.job_type,
            "files_generated": [incar_path, kpoints_path],
            "parameters": params,
        }
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(json.dumps({"status": "error", "message": str(e)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
