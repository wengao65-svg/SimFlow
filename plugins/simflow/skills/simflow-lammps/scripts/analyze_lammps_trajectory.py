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

try:
    from MDAnalysis import Universe
    from MDAnalysis.analysis.rdf import InterRDF
    from MDAnalysis.analysis.msd import EinsteinMSD
except ImportError:
    print(json.dumps({"status": "error", "message": "MDAnalysis not installed"}))
    sys.exit(1)


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


def analyze_lammps(data_file: str, dump_file: str, analyses: list) -> dict:
    """Run analyses on LAMMPS trajectory."""
    u = load_lammps_universe(data_file, dump_file)
    results = {"data_file": data_file, "dump_file": dump_file, "analyses": {}}

    n_frames = len(u.trajectory)
    results["n_frames"] = n_frames
    results["n_atoms"] = len(u.atoms)

    if "rdf" in analyses:
        results["analyses"]["rdf"] = compute_rdf(u)

    if "msd" in analyses:
        results["analyses"]["msd"] = compute_msd(u)

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
    args = parser.parse_args()

    try:
        result = analyze_lammps(args.data, args.dump, args.analyses)
        result["status"] = "success"
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(json.dumps({"status": "error", "message": str(e)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
