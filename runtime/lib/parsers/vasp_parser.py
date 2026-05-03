"""VASP output file parser.

Handles OUTCAR, OSZICAR, and EIGENVAL files. Extracts convergence info,
energies, forces, stress, and eigenvalues.
"""

import math
import re
from pathlib import Path

from ..parser import BaseParser, ParseResult


class VASPParser(BaseParser):
    """Parser for VASP output files."""

    software = "vasp"

    def parse(self, file_path: str) -> ParseResult:
        content = self._read_file(file_path)
        result = ParseResult(software="vasp", job_type="unknown", converged=False)

        fname = Path(file_path).name
        if fname == "OSZICAR" or fname.startswith("OSZICAR"):
            return self._parse_oszicar(content, result)
        elif fname == "OUTCAR" or fname.startswith("OUTCAR"):
            return self._parse_outcar(content, result)
        elif fname == "EIGENVAL" or fname.startswith("EIGENVAL"):
            return self._parse_eigenval(content, result)
        else:
            result.errors.append(f"Unknown VASP file type: {file_path}")
            return result

    def _parse_oszicar(self, content: str, result: ParseResult) -> ParseResult:
        """Parse OSZICAR for ionic step energies.

        Each ionic step ends with a line like:
            1 F= -.43362106E+02 E0= -.43362106E+02  d E =-.433621E+02
        DAV lines before it are SCF iterations within that ionic step.
        """
        lines = content.strip().split("\n")
        energies = []
        e0_energies = []
        scf_iterations = []

        current_scf_steps = 0
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("DAV:"):
                current_scf_steps += 1
            elif stripped and re.match(r"\d+\s+F=", stripped):
                # Ionic step line: "1 F= -.43362106E+02 E0= -.43362106E+02 ..."
                parts = stripped.split()
                try:
                    f_idx = parts.index("F=")
                    energies.append(float(parts[f_idx + 1]))
                except (ValueError, IndexError):
                    pass
                e0_match = re.search(r"E0=\s*([\d.Ee+-]+)", stripped)
                if e0_match:
                    e0_energies.append(float(e0_match.group(1)))
                scf_iterations.append(current_scf_steps)
                current_scf_steps = 0

        if e0_energies:
            result.final_energy = e0_energies[-1]
            result.total_energy = e0_energies[0]
        elif energies:
            result.final_energy = energies[-1]
            result.total_energy = energies[0]

        num_ionic = len(energies)
        result.converged = num_ionic > 0
        result.metadata["ionic_steps"] = num_ionic
        if scf_iterations:
            result.metadata["scf_iterations"] = scf_iterations
            result.metadata["total_scf_steps"] = sum(scf_iterations)

        # Detect job type from pattern
        if num_ionic == 1:
            result.job_type = "scf"
        else:
            result.job_type = "relaxation"

        return result

    def _parse_outcar(self, content: str, result: ParseResult) -> ParseResult:
        """Parse OUTCAR for convergence, energy, forces, stress, errors.

        Checks:
        - "reached required accuracy" → ionic relaxation converged
        - "aborting loop because EDIFF is reached" → SCF converged (per ionic step)
        - "VERY BAD NEWS!" → critical VASP error
        - "ZPOTRF" / "ZHEEV" → numerical errors
        - FORCES: max atom → max force on any atom
        - "in kB" → stress tensor
        - energy(sigma->0) → final energy
        """
        # Energy
        energy_match = re.search(r"energy\(sigma->0\)\s*=\s*([\d.Ee+-]+)", content)
        if energy_match:
            result.final_energy = float(energy_match.group(1))

        # INCAR parameters
        incar_match = re.search(r"ENCUT\s*=\s*([\d.]+)", content)
        if incar_match:
            result.parameters["encut"] = float(incar_match.group(1))

        # Ionic convergence
        ionic_converged = "reached required accuracy" in content
        result.converged = ionic_converged
        result.metadata["ionic_converged"] = ionic_converged

        # SCF convergence (count "aborting loop because EDIFF is reached")
        scf_converged_count = len(re.findall(
            r"aborting loop because EDIFF is reached", content
        ))
        result.metadata["scf_converged_steps"] = scf_converged_count

        # Forces: "FORCES: max atom, RMS     0.000000    0.000000"
        forces = []
        for m in re.finditer(
            r"FORCES: max atom, RMS\s+([\d.Ee+-]+)\s+([\d.Ee+-]+)", content
        ):
            forces.append({
                "max_atom": float(m.group(1)),
                "rms": float(m.group(2)),
            })
        if forces:
            result.forces = forces
            result.metadata["max_force"] = max(f["max_atom"] for f in forces)

        # Stress: "in kB" line (6 tensor components)
        stress = []
        for m in re.finditer(
            r"in kB\s+([\d.Ee+-]+)\s+([\d.Ee+-]+)\s+([\d.Ee+-]+)"
            r"\s+([\d.Ee+-]+)\s+([\d.Ee+-]+)\s+([\d.Ee+-]+)", content
        ):
            stress.append([float(m.group(i)) for i in range(1, 7)])
        if stress:
            result.stress = stress
            # Pressure = (XX + YY + ZZ) / 3
            last_stress = stress[-1]
            result.metadata["pressure_kB"] = sum(last_stress[:3]) / 3.0

        # Error detection
        if "VERY BAD NEWS!" in content:
            result.errors.append("VASP reported VERY BAD NEWS (numerical instability)")
            result.converged = False
        if "ZPOTRF" in content:
            result.errors.append("ZPOTRF error (Cholesky decomposition failed)")
            result.converged = False
        if "ZHEEV" in content:
            result.errors.append("ZHEEV error (eigenvalue solver failed)")
            result.converged = False

        # Warnings
        warning_count = content.count("WARNING")
        if warning_count > 0:
            result.warnings.append(f"{warning_count} WARNING(s) in OUTCAR")
            result.metadata["warning_count"] = warning_count

        # Determine job type from OUTCAR content
        if "aborting loop" in content and not ionic_converged:
            result.job_type = "scf"
        elif ionic_converged:
            result.job_type = "relaxation"
        else:
            result.job_type = "unknown"

        return result

    def _parse_eigenval(self, content: str, result: ParseResult) -> ParseResult:
        """Parse EIGENVAL file for band structure eigenvalues.

        Format:
            Line 1: NELECT NIONS ISPIN NKPTS
            Line 2: energy values (unused)
            Line 3: precision
            Line 4: "CAR" or "LINE"
            Line 5: system name
            Line 6: NBANDS NKPTS ISPIN
            Then for each k-point:
                blank line
                kx ky kz weight
                band_index eigenvalue occupation  (× NBANDS lines)

        Populates result.kpoints with eigenvalue data.
        """
        lines = content.strip().split("\n")
        if len(lines) < 6:
            result.errors.append("EIGENVAL file too short")
            return result

        # Header
        header1 = lines[0].split()
        header6 = lines[5].split()

        if len(header6) >= 3:
            nbands = int(header6[0])
            nkpts = int(header6[1])
            ispin = int(header6[2])
        else:
            result.errors.append("Cannot parse EIGENVAL header")
            return result

        kcoords = []
        eigenvalues = []
        occupations = []
        kpath_distances = [0.0]

        # Parse k-point blocks starting after header
        line_idx = 7  # Skip 6 header lines + first blank
        for kpt_idx in range(nkpts):
            # Skip blank lines
            while line_idx < len(lines) and not lines[line_idx].strip():
                line_idx += 1
            if line_idx >= len(lines):
                break

            # K-point coordinates and weight
            kparts = lines[line_idx].split()
            if len(kparts) >= 3:
                kx, ky, kz = float(kparts[0]), float(kparts[1]), float(kparts[2])
                kcoords.append([kx, ky, kz])

                # Cumulative k-path distance
                if kpt_idx > 0:
                    prev = kcoords[-2]
                    dk = math.sqrt(
                        (kx - prev[0]) ** 2 + (ky - prev[1]) ** 2 + (kz - prev[2]) ** 2
                    )
                    kpath_distances.append(kpath_distances[-1] + dk)
            line_idx += 1

            # Eigenvalues for this k-point
            kpt_eigenvalues = []
            kpt_occupations = []
            for band_idx in range(nbands):
                if line_idx >= len(lines):
                    break
                parts = lines[line_idx].split()
                if len(parts) >= 3:
                    kpt_eigenvalues.append(float(parts[1]))
                    kpt_occupations.append(float(parts[2]))
                line_idx += 1

            eigenvalues.append(kpt_eigenvalues)
            occupations.append(kpt_occupations)

        # Estimate Fermi energy: highest occupied eigenvalue
        fermi_energy = None
        for kpt_eigs, kpt_occs in zip(eigenvalues, occupations):
            for eig, occ in zip(kpt_eigs, kpt_occs):
                if occ > 0.5:
                    if fermi_energy is None or eig > fermi_energy:
                        fermi_energy = eig

        # Normalize k-path distances
        if kpath_distances and kpath_distances[-1] > 0:
            total = kpath_distances[-1]
            kpath_distances = [d / total for d in kpath_distances]

        result.kpoints = {
            "kcoords": kcoords,
            "kpath_distances": kpath_distances,
            "eigenvalues": eigenvalues,
            "occupations": occupations,
            "fermi_energy": fermi_energy,
            "nbands": nbands,
            "nkpts": nkpts,
            "ispin": ispin,
        }
        result.converged = True
        result.job_type = "bands"

        return result

    def check_convergence(self, file_path: str) -> dict:
        """Check convergence with detailed breakdown."""
        result = self.parse(file_path)
        return {
            "converged": result.converged,
            "final_energy": result.final_energy,
            "ionic_converged": result.metadata.get("ionic_converged"),
            "scf_converged_steps": result.metadata.get("scf_converged_steps"),
            "max_force": result.metadata.get("max_force"),
            "pressure_kB": result.metadata.get("pressure_kB"),
            "warnings": result.warnings,
            "errors": result.errors,
        }
