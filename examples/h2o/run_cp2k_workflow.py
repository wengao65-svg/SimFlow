#!/usr/bin/env python3
"""Prepare a redistributable CP2K AIMD-to-DFT example without execution."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
SIMFLOW_ROOT = SCRIPT_DIR.parent.parent
sys.path.insert(0, str(SIMFLOW_ROOT))

from runtime.simflow_helpers.engines.cp2k_input import (  # noqa: E402
    extract_last_frame,
    generate_input,
    read_cif_to_xyz,
    write_xyz,
)


CIF_FILE = SCRIPT_DIR / "H2O.cif"
AIMD_PARAMS = {
    "project_name": "H2O_aimd_nvt",
    "steps": 200,
    "timestep": 0.5,
    "temperature": 300.0,
}
ENERGY_PARAMS = {"project_name": "H2O_energy"}


def prepare_inputs(output_root: Path) -> dict:
    """Generate local CP2K inputs and describe the approval-bound handoff."""
    aimd_dir = output_root / "aimd"
    dft_dir = output_root / "dft_sp"
    aimd_dir.mkdir(parents=True, exist_ok=True)
    dft_dir.mkdir(parents=True, exist_ok=True)

    cell_abc, xyz_lines, element_counts = read_cif_to_xyz(str(CIF_FILE))
    cell = cell_abc.split()
    aimd_params = {
        **AIMD_PARAMS,
        "cell_a": cell[0],
        "cell_b": cell[1],
        "cell_c": cell[2],
        "coord_file": "structure.xyz",
    }
    aimd_input = aimd_dir / "aimd_nvt.inp"
    structure = aimd_dir / "structure.xyz"
    aimd_input.write_text(generate_input(aimd_params, "aimd_nvt"), encoding="utf-8")
    structure.write_text(
        write_xyz(len(xyz_lines), "H2O box from CIF", xyz_lines),
        encoding="utf-8",
    )

    generated = [aimd_input, structure]
    trajectory = aimd_dir / "H2O_aimd_nvt-pos-1.xyz"
    if trajectory.is_file():
        last_frame = dft_dir / "last_frame.xyz"
        last_frame.write_text(extract_last_frame(trajectory.read_text(encoding="utf-8")), encoding="utf-8")
        energy_params = {
            **ENERGY_PARAMS,
            "cell_a": cell[0],
            "cell_b": cell[1],
            "cell_c": cell[2],
            "coord_file": last_frame.name,
        }
        energy_input = dft_dir / "energy.inp"
        energy_input.write_text(generate_input(energy_params, "energy"), encoding="utf-8")
        generated.extend([last_frame, energy_input])

    summary = {
        "status": "prepared",
        "real_execution": False,
        "source_structure": str(CIF_FILE),
        "output_root": str(output_root),
        "atoms": len(xyz_lines),
        "elements": element_counts,
        "cell_abc": cell_abc,
        "generated_files": [str(path.relative_to(output_root)) for path in generated],
        "next_action": (
            "Prepare an exact scheduler script for these inputs, create an immutable hpc/plan, "
            "obtain approval bound to run_plan_hash, then use hpc/transfer and hpc/submit."
        ),
    }
    report = output_root / "dry_run_summary.json"
    report.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    summary["summary_path"] = str(report)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare CP2K AIMD-to-DFT inputs without execution")
    parser.add_argument("--dry-run", action="store_true", help="Retained for compatibility; execution is never performed")
    parser.add_argument("--output-dir", default=str(SCRIPT_DIR), help="Directory for generated inputs")
    args = parser.parse_args()

    if not CIF_FILE.is_file():
        parser.error(f"CIF file not found: {CIF_FILE}")
    summary = prepare_inputs(Path(args.output_dir).expanduser().resolve())
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
