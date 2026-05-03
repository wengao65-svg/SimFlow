#!/usr/bin/env python3
"""Generate VASP input files (INCAR, KPOINTS) from templates.

Reads templates from templates/vasp/ and applies parameters to produce
ready-to-use input files for VASP calculations.
"""

import argparse
import json
import re
import sys
from pathlib import Path


TEMPLATE_DIR = Path(__file__).resolve().parents[3] / "templates" / "vasp"


def render_template(template_content: str, variables: dict) -> str:
    """Render a Jinja-style template with {{ variable }} placeholders."""
    result = template_content
    for key, value in variables.items():
        pattern = r"\{\{\s*" + re.escape(key) + r"\s*(?:\|[^}]*)?\}\}"
        result = re.sub(pattern, str(value), result)
    return result


def generate_incar(job_type: str, params: dict, output_path: str) -> str:
    """Generate INCAR file from template."""
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

    defaults.update(params)
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
    parser.add_argument("--job-type", required=True, choices=["scf", "relax", "vc-relax", "md", "bands"],
                        help="Type of VASP calculation")
    parser.add_argument("--params", type=str, default="{}",
                        help="JSON string of parameters to override defaults")
    parser.add_argument("--output-dir", default=".", help="Output directory")
    args = parser.parse_args()

    try:
        params = json.loads(args.params)
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        incar_path = generate_incar(args.job_type, params, str(output_dir / "INCAR"))
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
