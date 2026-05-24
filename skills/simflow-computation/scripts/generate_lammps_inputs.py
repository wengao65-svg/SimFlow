#!/usr/bin/env python3
"""Generate LAMMPS input files (in.lammps, data file) from templates.

Reads templates from templates/lammps/ and applies parameters to produce
ready-to-use input files for LAMMPS simulations.
"""

import argparse
import json
import re
import sys
from pathlib import Path


TEMPLATE_DIR = Path(__file__).resolve().parents[3] / "templates" / "lammps"


def render_template(template_content: str, variables: dict) -> str:
    """Render a Jinja-style template with {{ variable }} placeholders."""
    result = template_content
    for key, value in variables.items():
        pattern = r"\{\{\s*" + re.escape(key) + r"\s*(?:\|[^}]*)?\}\}"
        result = re.sub(pattern, str(value), result)
    return result


def generate_input(job_type: str, params: dict, output_path: str) -> str:
    """Generate LAMMPS input script from template."""
    template_path = TEMPLATE_DIR / "in.lammps.template"
    if not template_path.exists():
        raise FileNotFoundError(f"Template not found: {template_path}")

    template = template_path.read_text()
    defaults = {
        "job_type": job_type,
        "units": "metal",
        "dimension": 3,
        "boundary": "p p p",
        "atom_style": "atomic",
        "data_file": "data.lammps",
        "pair_style": "eam/alloy",
        "potential_file": "Si.eam",
        "element": "Si",
        "timestep": 0.001,
        "thermo_interval": 100,
        "dump_interval": 100,
        "dump_file": "dump.lammps",
        "nsteps": 10000,
        "temperature": 300,
    }

    if job_type == "minimize":
        defaults.update({"min_style": "cg", "etol": 1e-6, "ftol": 1e-8,
                         "maxiter": 10000, "maxeval": 100000})
    elif job_type == "nvt":
        defaults.update({"temp_start": 300, "temp_end": 300, "tdamp": 0.1, "seed": 12345})
    elif job_type == "npt":
        defaults.update({"temp_start": 300, "temp_end": 300, "tdamp": 0.1,
                         "pressure": 0, "pdamp": 1.0, "seed": 12345})

    defaults.update(params)
    content = render_template(template, defaults)

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(content)
    return str(out)


def generate_data(params: dict, output_path: str) -> str:
    """Generate LAMMPS data file from template."""
    template_path = TEMPLATE_DIR / "data.template"
    if not template_path.exists():
        raise FileNotFoundError(f"Template not found: {template_path}")

    template = template_path.read_text()
    defaults = {
        "comment": "LAMMPS data file",
        "natoms": 8,
        "ntypes": 1,
        "xlo": 0.0, "xhi": 5.43,
        "ylo": 0.0, "yhi": 5.43,
        "zlo": 0.0, "zhi": 5.43,
        "atom_type": 1,
        "mass": 28.086,
    }
    defaults.update(params)
    content = render_template(template, defaults)

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(content)
    return str(out)


def main():
    parser = argparse.ArgumentParser(description="Generate LAMMPS input files")
    parser.add_argument("--job-type", required=True,
                        choices=["minimize", "nvt", "npt", "nve"],
                        help="Type of LAMMPS simulation")
    parser.add_argument("--params", type=str, default="{}",
                        help="JSON string of parameters to override defaults")
    parser.add_argument("--output-dir", default=".", help="Output directory")
    args = parser.parse_args()

    try:
        params = json.loads(args.params)
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        input_path = generate_input(args.job_type, params, str(output_dir / "in.lammps"))
        data_path = generate_data(params, str(output_dir / "data.lammps"))

        result = {
            "status": "success",
            "job_type": args.job_type,
            "files_generated": [input_path, data_path],
            "parameters": params,
        }
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(json.dumps({"status": "error", "message": str(e)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
