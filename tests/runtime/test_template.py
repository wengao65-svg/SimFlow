#!/usr/bin/env python3
"""Tests for template rendering engine."""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "runtime"))

from lib.template import (
    render_string, render_software_template, render_to_file,
    _process_variables, _process_if_blocks, _evaluate_condition,
)


def test_basic_variable_substitution():
    """Test simple {{ variable }} substitution."""
    template = "Hello {{ name }}!"
    result = render_string(template, {"name": "World"})
    assert result == "Hello World!"
    print("  basic substitution OK")


def test_default_values():
    """Test {{ variable | default(value) }}."""
    template = "ENCUT = {{ encut | default(520) }}"
    # With value provided
    result = render_string(template, {"encut": 600})
    assert result == "ENCUT = 600"
    # With default
    result = render_string(template, {})
    assert result == "ENCUT = 520"
    print("  default values OK")


def test_if_blocks():
    """Test {% if %} ... {% else %} ... {% endif %}."""
    template = "{% if calc %}Running{% else %}Not running{% endif %}"
    assert render_string(template, {"calc": True}) == "Running"
    assert render_string(template, {"calc": False}) == "Not running"
    assert render_string(template, {}) == "Not running"
    print("  if blocks OK")


def test_if_comparison():
    """Test {% if var == value %}."""
    template = '{% if job_type == "relax" %}Relaxation{% else %}SCF{% endif %}'
    assert render_string(template, {"job_type": "relax"}) == "Relaxation"
    assert render_string(template, {"job_type": "scf"}) == "SCF"
    print("  if comparison OK")


def test_for_loops():
    """Test {% for item in list %}."""
    template = "{% for m in modules %}module load {{ m }}\n{% endfor %}"
    result = render_string(template, {"modules": ["vasp/6.3.0", "intel/2022"]})
    assert "module load vasp/6.3.0" in result
    assert "module load intel/2022" in result
    print("  for loops OK")


def test_vasp_incar_template():
    """Test rendering VASP INCAR template."""
    result = render_software_template("vasp", "INCAR.template", {
        "job_type": "relax",
        "job_name": "Si_relax",
        "encut": 520,
        "ediff": "1E-6",
        "ibrion": 2,
        "nsw": 100,
    })
    assert "SYSTEM = Si_relax" in result
    assert "ENCUT  = 520" in result
    assert "NSW    = 100" in result
    assert "IBRION = 2" in result
    print("  VASP INCAR template OK")


def test_vasp_kpoints_template():
    """Test rendering VASP KPOINTS template."""
    result = render_software_template("vasp", "KPOINTS.template", {
        "kx": 6, "ky": 6, "kz": 6,
    })
    assert "6  6  6" in result
    print("  VASP KPOINTS template OK")


def test_vasp_poscar_template():
    """Test rendering VASP POSCAR template."""
    result = render_software_template("vasp", "POSCAR.template", {
        "comment": "Si diamond",
        "element_list": "Si",
        "atom_counts": "2",
        "coord_1": "0.0000 0.0000 0.0000",
        "coord_2": "0.2500 0.2500 0.2500",
    })
    assert "Si diamond" in result
    assert "Si" in result
    print("  VASP POSCAR template OK")


def test_qe_pw_in_template():
    """Test rendering QE pw.in template."""
    result = render_software_template("qe", "pw.in.template", {
        "calculation": "scf",
        "ecutwfc": 60.0,
        "nat": 2,
        "element": "Si",
    })
    assert "calculation  = 'scf'" in result
    assert "ecutwfc   = 60.0" in result
    assert "nat       = 2" in result
    print("  QE pw.in template OK")


def test_qe_relax_template():
    """Test QE template with relax calculation (conditional ions block)."""
    result = render_software_template("qe", "pw.in.template", {
        "calculation": "relax",
        "ion_dynamics": "bfgs",
    })
    assert "&IONS" in result
    assert "ion_dynamics = 'bfgs'" in result
    print("  QE relax template OK")


def test_lammps_nvt_template():
    """Test rendering LAMMPS template with NVT ensemble."""
    result = render_software_template("lammps", "in.lammps.template", {
        "job_type": "nvt",
        "temperature": 300,
        "nsteps": 50000,
        "data_file": "Si.data",
    })
    assert "nvt temp" in result
    assert "50000" in result
    assert "Si.data" in result
    print("  LAMMPS NVT template OK")


def test_lammps_minimize_template():
    """Test rendering LAMMPS template with minimize."""
    result = render_software_template("lammps", "in.lammps.template", {
        "job_type": "minimize",
        "etol": 1.0e-6,
    })
    assert "minimize" in result
    assert "min_style" in result
    print("  LAMMPS minimize template OK")


def test_slurm_template():
    """Test rendering SLURM submit script template."""
    result = render_software_template("vasp", "submit.slurm.template", {
        "job_name": "si_relax",
        "nodes": 2,
        "ntasks": 32,
        "walltime": "04:00:00",
        "modules": ["vasp/6.3.0"],
    })
    assert "#SBATCH --job-name=si_relax" in result
    assert "#SBATCH --nodes=2" in result
    assert "#SBATCH --ntasks=32" in result
    assert "module load vasp/6.3.0" in result
    print("  SLURM template OK")


def test_render_to_file():
    """Test rendering template to file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".INCAR", delete=False) as f:
        output_path = f.name

    try:
        render_to_file("vasp", "INCAR.template", {
            "job_type": "scf",
            "job_name": "Si_scf",
            "encut": 400,
        }, output_path)

        with open(output_path) as f:
            content = f.read()
        assert "SYSTEM = Si_scf" in content
        assert "ENCUT  = 400" in content
        print("  render to file OK")
    finally:
        import os
        os.unlink(output_path)


def test_nested_if():
    """Test nested if blocks."""
    template = '{% if a %}A{% if b %}B{% endif %}{% endif %}'
    assert render_string(template, {"a": True, "b": True}) == "AB"
    assert render_string(template, {"a": True, "b": False}) == "A"
    assert render_string(template, {"a": False, "b": True}) == ""
    print("  nested if OK")


def test_elif():
    """Test elif blocks."""
    template = '{% if x == 1 %}one{% elif x == 2 %}two{% else %}other{% endif %}'
    assert render_string(template, {"x": 1}) == "one"
    assert render_string(template, {"x": 2}) == "two"
    assert render_string(template, {"x": 3}) == "other"
    print("  elif OK")


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        print(f"  {t.__name__}...", end=" ")
        t()
        print("OK")
    print(f"\n  All {len(tests)} template tests passed!")
