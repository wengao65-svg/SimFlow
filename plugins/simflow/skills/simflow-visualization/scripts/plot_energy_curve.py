#!/usr/bin/env python3
"""Plot energy convergence curves from DFT/MD calculations.

Reads energy data from VASP OSZICAR, QE output, or LAMMPS logs
and generates convergence plots.
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
except ImportError:
    print(json.dumps({"status": "error", "message": "matplotlib not installed"}))
    sys.exit(1)


def parse_energies(file_path: str, software: str) -> dict:
    """Extract energy values from output files."""
    content = Path(file_path).read_text(errors="replace")

    if software == "vasp":
        # OSZICAR format: lines starting with space have energy in column 3
        energies = []
        for line in content.strip().split("\n"):
            if line.startswith(" "):
                parts = line.split()
                if len(parts) >= 3:
                    try:
                        energies.append(float(parts[2]))
                    except ValueError:
                        continue
        return {"energies": energies, "steps": list(range(1, len(energies) + 1))}

    elif software == "qe":
        # QE: look for !    total energy lines
        energies = []
        for line in content.split("\n"):
            if "!" in line and "total energy" in line:
                parts = line.split()
                for i, p in enumerate(parts):
                    if p == "energy" and i > 0:
                        try:
                            energies.append(float(parts[i - 1]))
                        except ValueError:
                            pass
                        break
        return {"energies": energies, "steps": list(range(1, len(energies) + 1))}

    elif software == "lammps":
        # LAMMPS log: look for thermo data after "Step" header
        energies = []
        in_thermo = False
        pe_col = -1
        for line in content.split("\n"):
            if line.startswith("Step"):
                parts = line.split()
                for i, p in enumerate(parts):
                    if p.lower() in ("pe", "poteng"):
                        pe_col = i
                        break
                in_thermo = True
                continue
            if in_thermo and line.strip() and not line.startswith("#"):
                parts = line.split()
                if pe_col >= 0 and len(parts) > pe_col:
                    try:
                        energies.append(float(parts[pe_col]))
                    except ValueError:
                        if "Loop" in line:
                            in_thermo = False
        return {"energies": energies, "steps": list(range(1, len(energies) + 1))}

    raise ValueError(f"Unsupported software: {software}")


def plot_energy_curve(
    energies: list, steps: list, output_path: str,
    title: str = "Energy Convergence",
    software: str = "unknown",
    reference_energy: float = None,
) -> dict:
    """Generate energy convergence plot."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

    # Absolute energy
    ax1.plot(steps, energies, "b-o", markersize=3, linewidth=1.5)
    ax1.set_xlabel("Step")
    ax1.set_ylabel("Energy (eV)")
    ax1.set_title(f"{title} - Absolute")
    ax1.grid(True, alpha=0.3)

    if reference_energy is not None:
        ax1.axhline(y=reference_energy, color="r", linestyle="--", label="Reference")
        ax1.legend()

    # Energy difference from final value
    if len(energies) > 1:
        final_e = energies[-1]
        delta_e = [e - final_e for e in energies]
        ax2.semilogy(steps, [abs(d) if abs(d) > 0 else 1e-15 for d in delta_e], "r-o",
                     markersize=3, linewidth=1.5)
        ax2.set_xlabel("Step")
        ax2.set_ylabel("|ΔE| (eV)")
        ax2.set_title(f"{title} - Convergence")
        ax2.grid(True, alpha=0.3)

    plt.tight_layout()

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(str(out), dpi=150, bbox_inches="tight")
    plt.close()

    return {
        "output": str(out),
        "num_steps": len(energies),
        "initial_energy": energies[0] if energies else None,
        "final_energy": energies[-1] if energies else None,
        "energy_change": energies[-1] - energies[0] if energies else None,
    }


def main():
    parser = argparse.ArgumentParser(description="Plot energy convergence curves")
    parser.add_argument("--file", required=True, help="Output file (OSZICAR, QE out, LAMMPS log)")
    parser.add_argument("--software", required=True, choices=["vasp", "qe", "lammps"],
                        help="Computational software")
    parser.add_argument("--output", default="energy_convergence.png", help="Output plot path")
    parser.add_argument("--title", default="Energy Convergence", help="Plot title")
    parser.add_argument("--reference-energy", type=float, help="Reference energy for comparison")
    args = parser.parse_args()

    try:
        data = parse_energies(args.file, args.software)
        result = plot_energy_curve(
            data["energies"], data["steps"], args.output,
            title=args.title, software=args.software,
            reference_energy=args.reference_energy,
        )
        result["status"] = "success"
        result["software"] = args.software
        result["input_file"] = args.file
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(json.dumps({"status": "error", "message": str(e)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
