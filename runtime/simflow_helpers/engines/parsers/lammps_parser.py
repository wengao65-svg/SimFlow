"""LAMMPS output file parser."""

import re
from ..parser import BaseParser, ParseResult


class LAMMPSParser(BaseParser):
    software = "lammps"

    def parse(self, file_path: str) -> ParseResult:
        content = self._read_file(file_path)
        result = ParseResult(software="lammps", job_type="md", converged=True)

        step_pattern = re.compile(r"^\s*(\d+)\s+([\d.Ee+-]+)\s+([\d.Ee+-]+)\s+([\d.Ee+-]+)", re.MULTILINE)
        thermo_data = step_pattern.findall(content)
        if thermo_data:
            result.metadata["thermo_steps"] = len(thermo_data)
            result.metadata["total_steps"] = int(thermo_data[-1][0])
            result.final_energy = float(thermo_data[-1][2])
            result.metadata["final_temp"] = float(thermo_data[-1][3])

        timestep_match = re.search(r"timestep\s+([\d.]+)", content)
        if timestep_match:
            result.parameters["timestep"] = float(timestep_match.group(1))

        return result

    def check_convergence(self, file_path: str) -> dict:
        result = self.parse(file_path)
        return {
            "converged": result.converged,
            "final_energy": result.final_energy,
            "final_temp": result.metadata.get("final_temp"),
            "warnings": result.warnings,
            "errors": result.errors,
        }
