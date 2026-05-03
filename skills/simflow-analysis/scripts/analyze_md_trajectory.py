#!/usr/bin/env python3
"""Analyze MD trajectories using MDAnalysis.

Computes radial distribution function (RDF), mean square displacement (MSD),
and diffusion coefficient from LAMMPS or VASP MD trajectory files.
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


def compute_rdf(topology: str, trajectory: str, sel1: str = "all", sel2: str = "all",
                rmax: float = 10.0, nbins: int = 200) -> dict:
    """Compute radial distribution function."""
    u = Universe(topology, trajectory)
    group1 = u.select_atoms(sel1)
    group2 = u.select_atoms(sel2)

    rdf = InterRDF(group1, group2, nbins=nbins, range=(0, rmax))
    rdf.run()

    return {
        "r": rdf.results.bins.tolist(),
        "g_r": rdf.results.rdf.tolist(),
        "rmax": rmax,
        "nbins": nbins,
        "selection_1": sel1,
        "selection_2": sel2,
    }


def compute_msd(topology: str, trajectory: str, select: str = "all") -> dict:
    """Compute mean square displacement and diffusion coefficient."""
    u = Universe(topology, trajectory)

    msd_analyzer = EinsteinMSD(u, select=select)
    msd_analyzer.run()

    msd_values = msd_analyzer.results.timeseries
    timestep = u.trajectory.dt
    n_frames = len(msd_values)

    # Compute diffusion coefficient from linear fit of MSD vs time
    times = np.arange(n_frames) * timestep
    if n_frames > 10:
        # Fit linear region (middle 60% of data)
        start = n_frames // 5
        end = 4 * n_frames // 5
        if end > start + 2:
            coeffs = np.polyfit(times[start:end], msd_values[start:end], 1)
            slope = coeffs[0]
            # D = slope / (2 * dimension) for 3D
            diffusion_coeff = slope / 6.0
        else:
            diffusion_coeff = None
    else:
        diffusion_coeff = None

    return {
        "times": times.tolist(),
        "msd": msd_values.tolist(),
        "timestep": timestep,
        "n_frames": n_frames,
        "diffusion_coefficient_ang2_per_ps": diffusion_coeff,
        "diffusion_coefficient_cm2_per_s": diffusion_coeff * 1e-4 if diffusion_coeff else None,
        "selection": select,
    }


def analyze_trajectory(topology: str, trajectory: str, analyses: list,
                       rdf_params: dict = None, msd_params: dict = None) -> dict:
    """Run requested analyses on an MD trajectory."""
    results = {"topology": topology, "trajectory": trajectory, "analyses": {}}

    if "rdf" in analyses:
        params = rdf_params or {}
        results["analyses"]["rdf"] = compute_rdf(
            topology, trajectory,
            sel1=params.get("sel1", "all"),
            sel2=params.get("sel2", "all"),
            rmax=params.get("rmax", 10.0),
            nbins=params.get("nbins", 200),
        )

    if "msd" in analyses:
        params = msd_params or {}
        results["analyses"]["msd"] = compute_msd(
            topology, trajectory,
            select=params.get("select", "all"),
        )

    return results


def main():
    parser = argparse.ArgumentParser(description="Analyze MD trajectories")
    parser.add_argument("--topology", required=True, help="Topology file (data.lammps, POSCAR, etc.)")
    parser.add_argument("--trajectory", required=True, help="Trajectory file (dump.lammps, XDATCAR, etc.)")
    parser.add_argument("--analyses", nargs="+", default=["rdf", "msd"],
                        choices=["rdf", "msd"], help="Analyses to perform")
    parser.add_argument("--rdf-sel1", default="all", help="RDF selection 1")
    parser.add_argument("--rdf-sel2", default="all", help="RDF selection 2")
    parser.add_argument("--rdf-rmax", type=float, default=10.0, help="RDF max radius (Angstrom)")
    parser.add_argument("--rdf-nbins", type=int, default=200, help="RDF number of bins")
    parser.add_argument("--msd-select", default="all", help="MSD atom selection")
    args = parser.parse_args()

    try:
        result = analyze_trajectory(
            args.topology, args.trajectory, args.analyses,
            rdf_params={"sel1": args.rdf_sel1, "sel2": args.rdf_sel2,
                        "rmax": args.rdf_rmax, "nbins": args.rdf_nbins},
            msd_params={"select": args.msd_select},
        )
        result["status"] = "success"
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(json.dumps({"status": "error", "message": str(e)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
