#!/usr/bin/env python3
"""Analyze LAMMPS trajectories using MDAnalysis.

Specialized wrapper for LAMMPS dump files. Computes RDF, MSD,
diffusion coefficient, and thermodynamic properties.
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np

_simflow_root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_simflow_root))

from runtime.simflow_core.script_contracts import add_helper_recording_args, maybe_record_helper_run

try:
    from MDAnalysis import Universe
    from MDAnalysis.analysis.rdf import InterRDF
    from MDAnalysis.analysis.msd import EinsteinMSD
except ImportError:
    print(json.dumps({"status": "error", "message": "MDAnalysis not installed"}))
    sys.exit(1)


def build_analysis_quality_manifest(
    *,
    n_frames: int,
    timestep: float | None,
    timestep_units: str | None,
    equilibration_start: int | None,
    analyses: list,
    error_estimates: dict | None = None,
) -> dict:
    """Record limits on trajectory-derived claims."""
    error_estimates = error_estimates or {}
    warnings = []
    if n_frames < 10:
        warnings.append({
            "code": "insufficient_frames_for_statistics",
            "message": "Trajectory has fewer than 10 frames; statistical claims should remain preliminary.",
        })
    if timestep is None:
        warnings.append({
            "code": "timestep_not_recorded",
            "message": "No timestep was recorded for analysis provenance or unit conversion.",
        })
    if equilibration_start is None:
        warnings.append({
            "code": "equilibration_boundary_not_recorded",
            "message": "No equilibration/production boundary was recorded.",
        })
    missing_error_estimates = [analysis for analysis in analyses if analysis not in error_estimates]
    if missing_error_estimates:
        warnings.append({
            "code": "analysis_error_estimates_missing",
            "message": "No uncertainty estimate was recorded for: " + ", ".join(missing_error_estimates),
        })
    return {
        "claim_scope": "analysis_support_only",
        "n_frames": n_frames,
        "timestep": timestep,
        "timestep_units": timestep_units,
        "equilibration_start": equilibration_start,
        "analyses": analyses,
        "error_estimates": error_estimates,
        "warnings": warnings,
        "claim_limits": [
            "Trajectory analysis supports derived-observable evidence only.",
            "No production MD claim should be made without equilibration, sampling, and uncertainty evidence.",
        ],
    }


def load_lammps_universe(data_file: str, dump_file: str) -> Universe:
    """Load LAMMPS data and dump files into MDAnalysis Universe."""
    return Universe(data_file, dump_file, format="LAMMPSDUMP")


def compute_rdf(u: Universe, sel1: str = "all", sel2: str = "all",
                rmax: float = 10.0, nbins: int = 200) -> dict:
    """Compute RDF from LAMMPS trajectory."""
    group1 = u.select_atoms(sel1)
    group2 = u.select_atoms(sel2)

    rdf = InterRDF(group1, group2, nbins=nbins, range=(0, rmax))
    rdf.run()

    # Find first peak
    rdf_values = rdf.results.rdf
    r_values = rdf.results.bins
    peak_idx = np.argmax(rdf_values)
    first_peak_r = r_values[peak_idx]
    first_peak_g = rdf_values[peak_idx]

    return {
        "r": r_values.tolist(),
        "g_r": rdf_values.tolist(),
        "first_peak_position": float(first_peak_r),
        "first_peak_height": float(first_peak_g),
        "rmax": rmax,
        "nbins": nbins,
    }


def compute_msd(u: Universe, select: str = "all") -> dict:
    """Compute MSD and diffusion coefficient from LAMMPS trajectory."""
    msd_analyzer = EinsteinMSD(u, select=select)
    msd_analyzer.run()

    msd_values = msd_analyzer.results.timeseries
    timestep = u.trajectory.dt
    n_frames = len(msd_values)
    times = np.arange(n_frames) * timestep

    # Diffusion coefficient from linear fit
    diffusion_coeff = None
    if n_frames > 10:
        start = n_frames // 5
        end = 4 * n_frames // 5
        if end > start + 2:
            coeffs = np.polyfit(times[start:end], msd_values[start:end], 1)
            diffusion_coeff = coeffs[0] / 6.0  # 3D: D = slope / 6

    return {
        "times": times.tolist(),
        "msd": msd_values.tolist(),
        "timestep": timestep,
        "n_frames": n_frames,
        "diffusion_coeff_ang2_per_ps": float(diffusion_coeff) if diffusion_coeff else None,
        "diffusion_coeff_cm2_per_s": float(diffusion_coeff * 1e-4) if diffusion_coeff else None,
    }


def analyze_lammps(
    data_file: str,
    dump_file: str,
    analyses: list,
    *,
    timestep_units: str | None = None,
    equilibration_start: int | None = None,
) -> dict:
    """Run analyses on LAMMPS trajectory."""
    u = load_lammps_universe(data_file, dump_file)
    results = {"data_file": data_file, "dump_file": dump_file, "analyses": {}}

    n_frames = len(u.trajectory)
    results["n_frames"] = n_frames
    results["n_atoms"] = len(u.atoms)
    timestep = getattr(u.trajectory, "dt", None)

    if "rdf" in analyses:
        results["analyses"]["rdf"] = compute_rdf(u)

    if "msd" in analyses:
        results["analyses"]["msd"] = compute_msd(u)

    results["analysis_quality"] = build_analysis_quality_manifest(
        n_frames=n_frames,
        timestep=timestep,
        timestep_units=timestep_units,
        equilibration_start=equilibration_start,
        analyses=analyses,
        error_estimates={},
    )

    return results


def main():
    parser = argparse.ArgumentParser(description="Analyze LAMMPS trajectories")
    parser.add_argument("--data", required=True, help="LAMMPS data file")
    parser.add_argument("--dump", required=True, help="LAMMPS dump file")
    parser.add_argument("--analyses", nargs="+", default=["rdf", "msd"],
                        choices=["rdf", "msd"], help="Analyses to perform")
    parser.add_argument("--rdf-rmax", type=float, default=10.0)
    parser.add_argument("--rdf-nbins", type=int, default=200)
    parser.add_argument("--msd-select", default="all")
    parser.add_argument("--timestep-units", default=None, help="Optional units for trajectory timestep metadata")
    parser.add_argument("--equilibration-start", type=int, default=None, help="First production frame index after equilibration")
    add_helper_recording_args(parser, default_stage="analysis_visualization")
    args = parser.parse_args()

    try:
        result = analyze_lammps(
            args.data,
            args.dump,
            args.analyses,
            timestep_units=args.timestep_units,
            equilibration_start=args.equilibration_start,
        )
        result["status"] = "success"
        result = maybe_record_helper_run(
            args=args,
            result=result,
            script_path=Path(__file__).resolve(),
            helper_name="lammps_analyze_trajectory",
            software="lammps",
            input_paths=[args.data, args.dump],
        )
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(json.dumps({"status": "error", "message": str(e)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
