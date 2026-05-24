"""Quantum ESPRESSO output file parser."""

import re
from ..parser import BaseParser, ParseResult


class QEParser(BaseParser):
    software = "quantum_espresso"

    def parse(self, file_path: str) -> ParseResult:
        content = self._read_file(file_path)
        result = ParseResult(software="quantum_espresso", job_type="unknown", converged=False)

        if "convergence has been achieved" in content.lower() or "End of BFGS" in content:
            result.converged = True

        energy_match = re.search(r"!\s*total energy\s*=\s*([\d.Ee+-]+)\s*Ry", content)
        if energy_match:
            result.final_energy = float(energy_match.group(1))

        ecutwfc_match = re.search(r"ecutwfc\s*=\s*([\d.]+)", content)
        if ecutwfc_match:
            result.parameters["ecutwfc"] = float(ecutwfc_match.group(1))

        if "CELL_PARAMETERS" in content or "bfgs" in content.lower():
            result.job_type = "relaxation"
        elif "ATOMIC_POSITIONS" in content:
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
