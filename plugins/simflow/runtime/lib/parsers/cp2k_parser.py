"""CP2K output file parser.

Handles .log (main output), .ener (energy per step), and -pos-1.xyz (trajectory).
Extracts convergence info, energies, temperature, and MD step data.
"""

import re
from pathlib import Path

from ..parser import BaseParser, ParseResult


class CP2KParser(BaseParser):
    """Parser for CP2K output files."""

    software = "cp2k"

    def parse(self, file_path: str) -> ParseResult:
        """Parse CP2K .log file.

        Extracts: converged, final_energy, job_type, warnings, errors,
        metadata (md_steps, temperature, scf_converged).
        """
        content = self._read_file(file_path)
        result = ParseResult(software="cp2k", job_type="unknown", converged=False)

        # Check normal termination
        if "PROGRAM ENDED AT" in content:
            result.converged = True

        # Detect job type: "GLOBAL| Run type  MD" or "RUN_TYPE MD"
        run_match = re.search(r"(?:GLOBAL\| Run type|RUN_TYPE)\s+(\w+)", content)
        if run_match:
            run_type = run_match.group(1).upper()
            if run_type == "MD":
                result.job_type = "md"
            elif run_type == "ENERGY":
                result.job_type = "energy"
            elif run_type in ("GEO_OPT", "CELL_OPT"):
                result.job_type = "relaxation"
            else:
                result.job_type = run_type.lower()

        # Extract final energy from FORCE_EVAL line
        # CP2K v2025.1: "ENERGY| Total FORCE_EVAL ( QS ) energy [hartree]  -2206.13"
        # Older CP2K:   "ENERGY| Total FORCE_EVAL ( QS ) energy (a.u.):     -34.123"
        energy_matches = re.findall(
            r"ENERGY\|\s+Total FORCE_EVAL\s.*?energy\s+(?:\[hartree\]|\(a\.u\.\):?)\s*([-\d.Ee+]+)",
            content,
        )
        if energy_matches:
            result.final_energy = float(energy_matches[-1])
            result.total_energy = float(energy_matches[0])

        # SCF convergence count
        scf_converged = len(re.findall(r"SCF run converged", content))
        result.metadata["scf_converged_steps"] = scf_converged

        # MD steps: "MD| Step number" (v2025.1) or "MD| Step Nr." (older)
        # Count unique step numbers (each step may appear in header + summary)
        step_matches = re.findall(
            r"MD\|\s+Step\s+(?:number|Nr\.)\s+(\d+)", content
        )
        md_steps = len(set(int(s) for s in step_matches)) if step_matches else 0
        result.metadata["md_steps"] = md_steps

        # Temperature from output
        # CP2K v2025.1: "MD| Temperature [K]  329.100751  319.524051"
        # Older CP2K:   "Temperature: 300.0 K"
        temp_matches = re.findall(
            r"MD\|\s+Temperature\s+\[K\]\s+([\d.]+)", content
        )
        if not temp_matches:
            temp_matches = re.findall(r"Temperature\s*:\s+([\d.]+)\s+K", content)
        if temp_matches:
            result.metadata["final_temperature"] = float(temp_matches[-1])

        # CP2K version: "CP2K| version string:  CP2K version 2025.1"
        version_match = re.search(
            r"CP2K\|\s+version\s+string:\s+CP2K\s+version\s+(\S+)", content
        )
        if not version_match:
            version_match = re.search(r"CP2K\|.*?version\s+(\d+\.\S+)", content)
        if version_match:
            result.metadata["cp2k_version"] = version_match.group(1)

        # Error detection
        if "ABORT" in content:
            result.errors.append("CP2K ABORT detected")
            result.converged = False
        if "SEGMENTATION FAULT" in content or "SIGSEGV" in content:
            result.errors.append("Segmentation fault detected")
            result.converged = False

        # Warning count
        # CP2K v2025.1: "The number of warnings for this run is : N"
        # Also check for inline warnings: "CP2K| WARNING" or "| WARNING |"
        warning_summary = re.search(
            r"The number of warnings for this run is\s*:\s*(\d+)", content
        )
        if warning_summary:
            warning_count = int(warning_summary.group(1))
        else:
            warning_count = len(re.findall(r"WARNING", content))
        if warning_count > 0:
            result.warnings.append(f"{warning_count} WARNING(s) in CP2K output")
            result.metadata["warning_count"] = warning_count

        return result

    def check_convergence(self, file_path: str) -> dict:
        """Check convergence with detailed breakdown."""
        result = self.parse(file_path)
        return {
            "converged": result.converged,
            "final_energy": result.final_energy,
            "job_type": result.job_type,
            "md_steps": result.metadata.get("md_steps"),
            "scf_converged_steps": result.metadata.get("scf_converged_steps"),
            "warnings": result.warnings,
            "errors": result.errors,
        }

    def parse_ener(self, file_path: str) -> dict:
        """Parse CP2K .ener file (energy per MD step).

        Format: Step Nr.  Time[fs]  Kin.[a.u.]  Temp[K]  Pot.[a.u.]  Cons Qty[a.u.]  UsedTime[s]

        Returns:
            Dict with lists: steps, times, kinetic, temperature, potential, cons_qty, used_time
        """
        content = self._read_file(file_path)
        data = {
            "steps": [],
            "times": [],
            "kinetic": [],
            "temperature": [],
            "potential": [],
            "cons_qty": [],
            "used_time": [],
        }

        for line in content.strip().split("\n"):
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("Step"):
                continue

            parts = line.split()
            if len(parts) >= 7:
                try:
                    data["steps"].append(int(parts[0]))
                    data["times"].append(float(parts[1]))
                    data["kinetic"].append(float(parts[2]))
                    data["temperature"].append(float(parts[3]))
                    data["potential"].append(float(parts[4]))
                    data["cons_qty"].append(float(parts[5]))
                    data["used_time"].append(float(parts[6]))
                except (ValueError, IndexError):
                    continue

        return data

    def parse_trajectory(self, file_path: str) -> list[dict]:
        """Parse CP2K trajectory XYZ file.

        CP2K extended XYZ format:
            natoms
            i = STEP, time = TIME_FS, E = ENERGY, ...
            Element  x  y  z
            ...

        Returns:
            List of frame dicts: [{step, time, energy, natoms, atoms: [{element, x, y, z}]}]
        """
        content = self._read_file(file_path)
        frames = []
        lines = content.strip().split("\n")
        i = 0

        while i < len(lines):
            line = lines[i].strip()
            if not line:
                i += 1
                continue

            # First line: natoms
            try:
                natoms = int(line)
            except ValueError:
                i += 1
                continue

            if i + 1 >= len(lines):
                break

            # Second line: comment with metadata
            # Format 1 (XYZ): "i = STEP, time = TIME, E = ENERGY"
            # Format 2 (EXTXYZ): "Lattice="..." Properties="..." Step=N Time=T Energy=E"
            comment = lines[i + 1].strip()
            step = None
            time_fs = None
            energy = None

            # Step: "i = N" or "Step=N"
            step_match = re.search(r"i\s*=\s*(\d+)", comment)
            if not step_match:
                step_match = re.search(r"\bStep=(\d+)", comment)
            if step_match:
                step = int(step_match.group(1))

            # Time: "time = T" or "Time=T"
            time_match = re.search(r"time\s*=\s*([\d.Ee+-]+)", comment)
            if not time_match:
                time_match = re.search(r"\bTime=([\d.Ee+-]+)", comment)
            if time_match:
                time_fs = float(time_match.group(1))

            # Energy: "E = E" or "Energy=E"
            energy_match = re.search(r"\bE\s*=\s*([\d.Ee+-]+)", comment)
            if not energy_match:
                energy_match = re.search(r"\bEnergy=([\d.Ee+-]+)", comment)
            if energy_match:
                energy = float(energy_match.group(1))

            # Atom lines
            atoms = []
            for j in range(i + 2, min(i + 2 + natoms, len(lines))):
                parts = lines[j].split()
                if len(parts) >= 4:
                    atoms.append({
                        "element": parts[0],
                        "x": float(parts[1]),
                        "y": float(parts[2]),
                        "z": float(parts[3]),
                    })

            if len(atoms) == natoms:
                frames.append({
                    "step": step,
                    "time": time_fs,
                    "energy": energy,
                    "natoms": natoms,
                    "atoms": atoms,
                })

            i += 2 + natoms

        return frames
