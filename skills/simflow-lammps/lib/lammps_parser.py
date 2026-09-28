"""Read basic thermo data from a LAMMPS log without inferring completion."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ParseResult:
    final_energy: float | None = None
    converged: bool = False
    parameters: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class LAMMPSParser:
    """Parse selected thermo fields; absence of an error is not convergence."""

    def parse(self, file_path: str) -> ParseResult:
        content = Path(file_path).read_text(encoding="utf-8", errors="replace")
        result = ParseResult()
        step_pattern = re.compile(
            r"^\s*(\d+)\s+([\d.Ee+-]+)\s+([\d.Ee+-]+)\s+([\d.Ee+-]+)\s+([\d.Ee+-]+)",
            re.MULTILINE,
        )
        thermo_data = step_pattern.findall(content)
        if thermo_data:
            result.metadata["thermo_steps"] = len(thermo_data)
            result.metadata["total_steps"] = int(thermo_data[-1][0])
            result.final_energy = float(thermo_data[-1][4])
            result.metadata["final_temp"] = float(thermo_data[-1][1])
            result.metadata["final_potential_energy"] = float(thermo_data[-1][2])
            result.metadata["final_kinetic_energy"] = float(thermo_data[-1][3])
        else:
            result.warnings.append("No matching thermo rows were found.")
        timestep_match = re.search(r"timestep\s+([\d.]+)", content)
        if timestep_match:
            result.parameters["timestep"] = float(timestep_match.group(1))
        result.metadata["run_finished_marker_present"] = "Loop time of" in content
        result.warnings.append("Thermo parsing alone cannot establish scientific convergence.")
        return result
