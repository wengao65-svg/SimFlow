"""Gaussian output file parser."""

import re
from ..parser import BaseParser, ParseResult


class GaussianParser(BaseParser):
    software = "gaussian"

    def parse(self, file_path: str) -> ParseResult:
        content = self._read_file(file_path)
        result = ParseResult(software="gaussian", job_type="unknown", converged=False)

        if "Stationary point found" in content or "Normal termination" in content:
            result.converged = True

        energy_match = re.search(r"SCF Done:\s+E\(.+?\)\s*=\s*([\d.Ee+-]+)", content)
        if energy_match:
            result.final_energy = float(energy_match.group(1))

        method_match = re.search(r"#\s*(\S+)\s*/\s*(\S+)", content)
        if method_match:
            result.parameters["method"] = method_match.group(1)
            result.parameters["basis"] = method_match.group(2)

        if "Optimization" in content:
            result.job_type = "optimization"
        elif "Freq" in content or "Frequency" in content:
            result.job_type = "frequency"
        else:
            result.job_type = "sp"

        imaginary = re.findall(r"Frequencies\s*--\s*([\d.-]+)\s*([\d.-]+)\s*([\d.-]+)", content)
        for freqs in imaginary:
            for f in freqs:
                if float(f) < 0:
                    result.warnings.append(f"Imaginary frequency: {f}")

        return result

    def check_convergence(self, file_path: str) -> dict:
        result = self.parse(file_path)
        return {
            "converged": result.converged,
            "final_energy": result.final_energy,
            "imaginary_frequencies": len(result.warnings) > 0,
            "warnings": result.warnings,
            "errors": result.errors,
        }
