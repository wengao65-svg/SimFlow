#!/usr/bin/env python3
"""Analyze MD trajectories using MDAnalysis.

Computes radial distribution function (RDF), mean square displacement (MSD),
and diffusion coefficient from LAMMPS or VASP MD trajectory files. Engine
agnostic; LAMMPS-specific dump metadata (image flags, units style) is inspected
as intake evidence but property-analysis claims remain owned by the
analysis_visualization stage.
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


def load_universe(topology: str, trajectory: str, *,
                  topology_format: str | None = None,
                  trajectory_format: str | None = None) -> Universe:
    """Load topology and trajectory into a single MDAnalysis Universe.

    Pass ``topology_format``/``trajectory_format`` (e.g. ``LAMMPSDUMP`` for a
    LAMMPS dump used as both topology and trajectory, or ``DATA``+``LAMMPSDUMP``
    for a LAMMPS data file + dump) when MDAnalysis cannot infer the format from
    the file extension.
    """
    return Universe(
        topology,
        trajectory,
        topology_format=topology_format,
        format=trajectory_format,
    )


def inspect_trajectory_intake(u: Universe, timestep_units: str | None) -> dict:
    """Record engine-agnostic trajectory metadata that affects analysis validity.

    LAMMPS-specific dump semantics (image flags, scaled coordinates, units
    style) belong to the LAMMPS intake manifest produced by
    ``parse_lammps_outputs.py``; this function records only the engine-agnostic
    provenance that any downstream property analysis depends on.
    """
    n_frames = len(u.trajectory)
    n_atoms = len(u.atoms)
    dt = getattr(u.trajectory, "dt", None)

    warnings = []
    if timestep_units is None:
        warnings.append({
            "code": "timestep_units_not_specified",
            "message": "timestep_units not provided; physical-unit conversions and provenance are ambiguous.",
        })

    return {
        "n_frames": n_frames,
        "n_atoms": n_atoms,
        "timestep": dt,
        "timestep_units": timestep_units,
        "warnings": warnings,
    }


def build_analysis_quality_manifest(
    *,
    n_frames: int,
    timestep: float | None,
    timestep_units: str | None,
    equilibration_start: int | None,
    analyses: list,
    intake_warnings: list | None = None,
    error_estimates: dict | None = None,
) -> dict:
    """Record limits on trajectory-derived claims."""
    error_estimates = error_estimates or {}
    intake_warnings = intake_warnings or []
    warnings = list(intake_warnings)

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
    missing_error_estimates = [a for a in analyses if a not in error_estimates]
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


def compute_rdf(u: Universe, sel1: str = "all", sel2: str = "all",
                rmax: float = 10.0, nbins: int = 200,
                equilibration_start: int | None = None) -> dict:
    """Compute radial distribution function over the production window."""
    group1 = u.select_atoms(sel1)
    group2 = u.select_atoms(sel2)

    rdf = InterRDF(group1, group2, nbins=nbins, range=(0, rmax))
    if equilibration_start is not None:
        rdf.run(start=equilibration_start)
    else:
        rdf.run()

    rdf_values = rdf.results.rdf
    r_values = rdf.results.bins
    peak_idx = int(np.argmax(rdf_values)) if len(rdf_values) else None
    first_peak_r = float(r_values[peak_idx]) if peak_idx is not None else None
    first_peak_g = float(rdf_values[peak_idx]) if peak_idx is not None else None

    return {
        "r": r_values.tolist(),
        "g_r": rdf_values.tolist(),
        "first_peak_position": first_peak_r,
        "first_peak_height": first_peak_g,
        "rmax": rmax,
        "nbins": nbins,
        "selection_1": sel1,
        "selection_2": sel2,
        "equilibration_start": equilibration_start,
    }


def compute_msd(u: Universe, select: str = "all",
                equilibration_start: int | None = None,
                timestep_units: str | None = None) -> dict:
    """Compute MSD and diffusion coefficient over the production window.

    Diffusion coefficient is fit on the middle 60% of the production MSD. The
    cm^2/s conversion (1 A^2/ps = 1e-4 cm^2/s) is emitted only when
    ``timestep_units == "ps"``; otherwise it is left null to avoid silent
    unit errors for lj/si/electron ensembles.
    """
    msd_analyzer = EinsteinMSD(u, select=select, fft=True)
    try:
        if equilibration_start is not None:
            msd_analyzer.run(start=equilibration_start)
        else:
            msd_analyzer.run()
    except ImportError:
        msd_analyzer = EinsteinMSD(u, select=select, fft=False)
        if equilibration_start is not None:
            msd_analyzer.run(start=equilibration_start)
        else:
            msd_analyzer.run()

    msd_values = msd_analyzer.results.timeseries
    timestep = getattr(u.trajectory, "dt", None)
    n_frames = len(msd_values)
    times = np.arange(n_frames) * (timestep if timestep is not None else 1.0)

    diffusion_coeff = None
    fit_window = None
    if n_frames > 10:
        start = n_frames // 5
        end = 4 * n_frames // 5
        if end > start + 2:
            coeffs = np.polyfit(times[start:end], msd_values[start:end], 1)
            diffusion_coeff = float(coeffs[0] / 6.0)
            fit_window = {"start": int(start), "stop": int(end)}

    units_are_ps = timestep_units == "ps"
    diffusion_cm2_s = float(diffusion_coeff * 1e-4) if (diffusion_coeff is not None and units_are_ps) else None

    return {
        "times": times.tolist(),
        "msd": msd_values.tolist(),
        "timestep": timestep,
        "timestep_units": timestep_units,
        "n_frames": n_frames,
        "fit_window": fit_window,
        "diffusion_coefficient_ang2_per_ps": diffusion_coeff if units_are_ps else None,
        "diffusion_coefficient_cm2_per_s": diffusion_cm2_s,
        "diffusion_coefficient_raw": diffusion_coeff,
        "selection": select,
        "equilibration_start": equilibration_start,
    }


def analyze_trajectory(topology: str, trajectory: str, analyses: list,
                       rdf_params: dict | None = None, msd_params: dict | None = None,
                       *, timestep_units: str | None = None,
                       equilibration_start: int | None = None,
                       topology_format: str | None = None,
                       trajectory_format: str | None = None) -> dict:
    """Run requested analyses on a single loaded trajectory."""
    u = load_universe(topology, trajectory, topology_format=topology_format,
                      trajectory_format=trajectory_format)
    intake = inspect_trajectory_intake(u, timestep_units)
    results: dict = {
        "topology": topology,
        "trajectory": trajectory,
        "analyses": {},
        "intake": intake,
    }

    if "rdf" in analyses:
        params = rdf_params or {}
        results["analyses"]["rdf"] = compute_rdf(
            u,
            sel1=params.get("sel1", "all"),
            sel2=params.get("sel2", "all"),
            rmax=params.get("rmax", 10.0),
            nbins=params.get("nbins", 200),
            equilibration_start=equilibration_start,
        )

    if "msd" in analyses:
        params = msd_params or {}
        results["analyses"]["msd"] = compute_msd(
            u,
            select=params.get("select", "all"),
            equilibration_start=equilibration_start,
            timestep_units=timestep_units,
        )

    results["analysis_quality"] = build_analysis_quality_manifest(
        n_frames=intake["n_frames"],
        timestep=intake["timestep"],
        timestep_units=timestep_units,
        equilibration_start=equilibration_start,
        analyses=analyses,
        intake_warnings=intake["warnings"],
        error_estimates={},
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
    parser.add_argument("--timestep-units", default=None,
                        help="Units of trajectory timestep for provenance and unit conversion (e.g. ps, fs, s, lj). "
                             "cm^2/s conversion is only emitted when 'ps'.")
    parser.add_argument("--topology-format", default=None,
                        help="MDAnalysis topology format hint (e.g. LAMMPSDATA, POSCAR) when extension is ambiguous.")
    parser.add_argument("--trajectory-format", default=None,
                        help="MDAnalysis trajectory format hint (e.g. LAMMPSDUMP, XDATCAR) when extension is ambiguous.")
    parser.add_argument("--equilibration-start", type=int, default=None,
                        help="First production frame index; RDF/MSD are computed from this frame onward.")
    add_helper_recording_args(parser, default_stage="analysis_visualization")
    args = parser.parse_args()

    try:
        result = analyze_trajectory(
            args.topology, args.trajectory, args.analyses,
            rdf_params={"sel1": args.rdf_sel1, "sel2": args.rdf_sel2,
                        "rmax": args.rdf_rmax, "nbins": args.rdf_nbins},
            msd_params={"select": args.msd_select},
            timestep_units=args.timestep_units,
            equilibration_start=args.equilibration_start,
            topology_format=args.topology_format,
            trajectory_format=args.trajectory_format,
        )
        result["status"] = "success"
        result = maybe_record_helper_run(
            args=args,
            result=result,
            script_path=Path(__file__).resolve(),
            helper_name="analyze_md_trajectory",
            input_paths=[args.topology, args.trajectory],
        )
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(json.dumps({"status": "error", "message": str(e)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
