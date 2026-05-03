#!/usr/bin/env python3
"""Plot VASP band structure from EIGENVAL and KPOINTS files.

Usage:
    python plot_band_structure.py --eigenval EIGENVAL --kpoints KPOINTS -o bands.png

Supports KPOINTS in line-mode with high-symmetry labels (lines starting with !).
Falls back to auto-detecting segment boundaries from k-coordinate jumps.
"""

import argparse
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "runtime"))
from lib.parsers.vasp_parser import VASPParser


def parse_kpoints_labels(kpoints_path: str) -> list[tuple[list[float], str]]:
    """Parse KPOINTS file for high-symmetry points with labels.

    Returns list of (kcoord, label) for lines containing '!' labels.
    Only works with line-mode KPOINTS.
    """
    labels = []
    with open(kpoints_path) as f:
        lines = f.readlines()

    for line in lines:
        stripped = line.strip()
        if "!" in stripped:
            parts = stripped.split("!")
            kpart = parts[0].strip()
            label = parts[1].strip()
            coords = [float(x) for x in kpart.split()[:3]]
            labels.append((coords, label))
    return labels


def compute_segment_boundaries(
    kcoords: list[list[float]], labeled_points: list[tuple[list[float], str]],
) -> list[tuple[int, str]]:
    """Find k-point indices that match labeled high-symmetry points.

    Returns list of (index, label) for boundaries.
    """
    boundaries = []
    for kpt, label in labeled_points:
        best_idx = 0
        best_dist = float("inf")
        for i, kc in enumerate(kcoords):
            d = math.sqrt(
                (kc[0] - kpt[0]) ** 2
                + (kc[1] - kpt[1]) ** 2
                + (kc[2] - kpt[2]) ** 2
            )
            if d < best_dist:
                best_dist = d
                best_idx = i
        if best_dist < 0.01:
            boundaries.append((best_idx, label))
    return boundaries


def detect_segment_boundaries(
    kcoords: list[list[float]], kpath_distances: list[float],
) -> list[int]:
    """Auto-detect segment boundaries from k-path distance jumps.

    When KPOINTS labels are unavailable, find points where the
    inter-kpoint distance is much larger than average (segment boundaries
    in line-mode cause distance resets).
    """
    if len(kpath_distances) < 3:
        return []

    # Compute per-step distances
    dk = [kpath_distances[i] - kpath_distances[i - 1] for i in range(1, len(kpath_distances))]
    if not dk:
        return []

    median_dk = sorted(dk)[len(dk) // 2]
    boundaries = [0]
    for i, d in enumerate(dk):
        if d > median_dk * 5:
            boundaries.append(i + 1)
    return boundaries


def plot_band_structure(
    eigenval_path: str,
    kpoints_path: str | None = None,
    output_path: str = "bands.png",
    efermi: float | None = None,
    emin: float | None = None,
    emax: float | None = None,
    title: str = "Band Structure",
    show: bool = False,
) -> str:
    """Plot band structure and save to file.

    Args:
        eigenval_path: Path to EIGENVAL file
        kpoints_path: Path to KPOINTS file (optional, for labels)
        output_path: Output image path
        efermi: Fermi energy override (auto-estimated if None)
        emin: Min energy for y-axis
        emax: Max energy for y-axis
        title: Plot title
        show: Show interactive plot instead of saving

    Returns:
        Path to saved image
    """
    import matplotlib
    if not show:
        matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    # Parse EIGENVAL
    parser = VASPParser()
    result = parser.parse(eigenval_path)
    if result.errors:
        raise ValueError(f"EIGENVAL parse errors: {result.errors}")

    kp = result.kpoints
    kcoords = kp["kcoords"]
    eigenvalues = kp["eigenvalues"]
    occupations = kp["occupations"]
    nkpts = kp["nkpts"]
    nbands = kp["nbands"]

    # Use provided Fermi energy or estimate from parser
    ef = efermi if efermi is not None else kp.get("fermi_energy", 0.0)

    # Compute k-path distances
    distances = kp.get("kpath_distances")
    if not distances or len(distances) != nkpts + 1:
        # Fallback: compute from kcoords
        distances = [0.0]
        for i in range(1, len(kcoords)):
            dk = math.sqrt(
                (kcoords[i][0] - kcoords[i - 1][0]) ** 2
                + (kcoords[i][1] - kcoords[i - 1][1]) ** 2
                + (kcoords[i][2] - kcoords[i - 1][2]) ** 2
            )
            distances.append(distances[-1] + dk)
        total = distances[-1]
        if total > 0:
            distances = [d / total for d in distances]

    # Use nkpts distances (not nkpts+1)
    kdist = distances[:nkpts] if len(distances) >= nkpts else distances

    # High-symmetry labels
    boundaries = []
    if kpoints_path and Path(kpoints_path).exists():
        labeled = parse_kpoints_labels(kpoints_path)
        if labeled:
            boundaries = compute_segment_boundaries(kcoords, labeled)

    if not boundaries:
        # Auto-detect from distance jumps
        boundary_indices = detect_segment_boundaries(kcoords, kdist)
        boundaries = [(idx, f"k{idx}") for idx in boundary_indices]

    # Shift energies relative to Fermi level
    fig, ax = plt.subplots(figsize=(8, 6))

    for band_idx in range(nbands):
        band_e = [eigenvalues[k][band_idx] - ef for k in range(nkpts)]
        ax.plot(kdist, band_e, color="blue", linewidth=0.5, alpha=0.8)

    # Fermi level
    ax.axhline(y=0, color="red", linestyle="--", linewidth=0.8, label=f"E_F = {ef:.3f} eV")

    # High-symmetry point labels
    if boundaries:
        boundary_dists = []
        boundary_labels = []
        for idx, label in boundaries:
            if idx < len(kdist):
                boundary_dists.append(kdist[idx])
                # Clean up LaTeX-style labels
                if "Gamma" in label or "GAMMA" in label:
                    clean = r"$\Gamma$"
                else:
                    clean = label
                boundary_labels.append(clean)
            ax.axvline(x=kdist[idx] if idx < len(kdist) else 0, color="gray", linewidth=0.3)
        ax.set_xticks(boundary_dists)
        ax.set_xticklabels(boundary_labels)

    # Energy range
    all_e = [eigenvalues[k][b] - ef for k in range(nkpts) for b in range(nbands)]
    if emin is None:
        emin = max(min(all_e), -15)
    if emax is None:
        emax = min(max(all_e), 15)
    ax.set_ylim(emin, emax)

    ax.set_xlim(kdist[0], kdist[-1])
    ax.set_ylabel("Energy - E_F (eV)")
    ax.set_xlabel("k-path")
    ax.set_title(title)
    ax.legend(loc="upper right")

    plt.tight_layout()
    if show:
        plt.show()
    else:
        fig.savefig(output_path, dpi=300, bbox_inches="tight")
        print(f"Band structure saved to {output_path}")
    plt.close(fig)
    return output_path


def main():
    parser = argparse.ArgumentParser(description="Plot VASP band structure")
    parser.add_argument("--eigenval", required=True, help="Path to EIGENVAL file")
    parser.add_argument("--kpoints", default=None, help="Path to KPOINTS file (for labels)")
    parser.add_argument("-o", "--output", default="bands.png", help="Output image path")
    parser.add_argument("--efermi", type=float, default=None, help="Fermi energy (eV)")
    parser.add_argument("--emin", type=float, default=None, help="Min energy for y-axis")
    parser.add_argument("--emax", type=float, default=None, help="Max energy for y-axis")
    parser.add_argument("--title", default="Band Structure", help="Plot title")
    parser.add_argument("--show", action="store_true", help="Show interactive plot")
    args = parser.parse_args()

    plot_band_structure(
        eigenval_path=args.eigenval,
        kpoints_path=args.kpoints,
        output_path=args.output,
        efermi=args.efermi,
        emin=args.emin,
        emax=args.emax,
        title=args.title,
        show=args.show,
    )


if __name__ == "__main__":
    main()
