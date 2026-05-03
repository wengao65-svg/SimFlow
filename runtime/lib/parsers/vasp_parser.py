"""VASP output file parser."""

import re
from ..parser import BaseParser, ParseResult


class VASPParser(BaseParser):
    """Parser for VASP output files (OUTCAR, OSZICAR, vasprun.xml)."""

    software = "vasp"

    def parse(self, file_path: str) -> ParseResult:
        content = self._read_file(file_path)
        result = ParseResult(software="vasp", job_type="unknown", converged=False)

        if file_path.endswith("OSZICAR"):
            return self._parse_oszicar(content, result)
        elif file_path.endswith("OUTCAR"):
            return self._parse_outcar(content, result)
        else:
            result.errors.append(f"Unknown VASP file type: {file_path}")
            return result

    def _parse_oszicar(self, content: str, result: ParseResult) -> ParseResult:
        lines = content.strip().split("\n")
        energies = []
        for line in lines:
            if line.startswith(" "):
                parts = line.split()
                if len(parts) >= 3:
                    try:
                        energies.append(float(parts[2]))
                    except ValueError:
                        continue
        if energies:
            result.final_energy = energies[-1]
            result.total_energy = energies[0]
            result.converged = len(energies) > 1
            result.metadata["ionic_steps"] = len(energies)
        result.job_type = "relaxation"
        return result

    def _parse_outcar(self, content: str, result: ParseResult) -> ParseResult:
        if "reached required accuracy" in content:
            result.converged = True
        energy_match = re.search(r"energy\(sigma->0\)\s*=\s*([\d.Ee+-]+)", content)
        if energy_match:
            result.final_energy = float(energy_match.group(1))
        incar_match = re.search(r"ENCUT\s*=\s*([\d.]+)", content)
        if incar_match:
            result.parameters["encut"] = float(incar_match.group(1))
        result.job_type = "scf"
        return result

    def check_convergence(self, file_path: str) -> dict:
        result = self.parse(file_path)
        return {
            "converged": result.converged,
            "final_energy": result.final_energy,
            "warnings": result.warnings,
            "errors": result.errors,
        }
