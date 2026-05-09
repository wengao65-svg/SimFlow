"""CP2K output parsing for common SimFlow workflows."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from ..parser import BaseParser, ParseResult


_RUN_TYPE_TO_JOB = {
    "ENERGY": "energy",
    "GEO_OPT": "geo_opt",
    "CELL_OPT": "cell_opt",
    "MD": "md",
}


class CP2KParser(BaseParser):
    """Parser for CP2K text outputs and lightweight restart metadata."""

    software = "cp2k"

    def parse(self, file_path: str) -> ParseResult:
        """Parse a CP2K `.log` file."""
        content = self._read_file(file_path)
        result = ParseResult(software="cp2k", job_type="unknown", converged=False)

        run_type = self._match_first(
            content,
            r"GLOBAL\|\s+Run type\s+([A-Z_]+)",
            r"\bRUN_TYPE\s+([A-Z_]+)",
        )
        if run_type:
            normalized = run_type.upper()
            result.job_type = _RUN_TYPE_TO_JOB.get(normalized, normalized.lower())
            result.metadata["run_type"] = normalized

        project = self._match_first(
            content,
            r"GLOBAL\|\s+Project name\s+([^\s]+)",
            r"\bPROJECT\s+([^\s]+)",
        )
        if project:
            result.metadata["project_name"] = project

        version = self._match_first(
            content,
            r"CP2K\|\s+version string:\s+CP2K version\s+(\S+)",
            r"CP2K\|.*?version\s+(\d+\.\S+)",
        )
        if version:
            result.metadata["cp2k_version"] = version

        normal_end = "PROGRAM ENDED AT" in content
        result.metadata["normal_end"] = normal_end
        result.converged = normal_end

        energy_matches = re.findall(
            r"ENERGY\|\s+Total FORCE_EVAL\s.*?energy\s+(?:\[hartree\]|\(a\.u\.\):?)\s*([-\d.Ee+]+)",
            content,
        )
        if energy_matches:
            result.total_energy = float(energy_matches[0])
            result.final_energy = float(energy_matches[-1])

        scf_steps = len(re.findall(r"SCF run converged", content))
        result.metadata["scf_converged_steps"] = scf_steps
        result.metadata["scf_converged"] = scf_steps > 0

        step_matches = re.findall(r"MD\|\s+Step\s+(?:number|Nr\.)\s+(\d+)", content)
        result.metadata["md_steps"] = len({int(item) for item in step_matches}) if step_matches else 0

        temp_matches = re.findall(r"MD\|\s+Temperature\s+\[K\]\s+([-\d.Ee+]+)", content)
        if not temp_matches:
            temp_matches = re.findall(r"Temperature\s*:\s*([-\d.Ee+]+)\s+K", content)
        if temp_matches:
            result.metadata["final_temperature"] = float(temp_matches[-1])

        time_matches = re.findall(r"CPU TIME\s*\|\s*([-\d.Ee+]+)", content)
        if time_matches:
            result.metadata["used_time"] = float(time_matches[-1])

        if "ABORT" in content:
            result.errors.append("CP2K ABORT detected")
            result.metadata["abort_detected"] = True
            result.converged = False
        else:
            result.metadata["abort_detected"] = False

        error_lines = re.findall(r"^\s*(?:ABORT|ERROR).*", content, flags=re.MULTILINE)
        if error_lines:
            result.metadata["error_lines"] = error_lines
            if not result.errors:
                result.errors.extend(error_lines)
        if "SEGMENTATION FAULT" in content or "SIGSEGV" in content:
            result.errors.append("Segmentation fault detected")
            result.converged = False

        warning_summary = re.search(r"The number of warnings for this run is\s*:\s*(\d+)", content)
        if warning_summary:
            warning_count = int(warning_summary.group(1))
        else:
            warning_count = len(re.findall(r"WARNING", content))
        result.metadata["warning_count"] = warning_count
        if warning_count:
            result.warnings.append(f"{warning_count} WARNING(s) in CP2K output")

        return result

    def check_convergence(self, file_path: str) -> dict[str, Any]:
        """Check convergence of a CP2K log with a small structured summary."""
        result = self.parse(file_path)
        return {
            "converged": result.converged,
            "job_type": result.job_type,
            "run_type": result.metadata.get("run_type"),
            "project_name": result.metadata.get("project_name"),
            "final_energy": result.final_energy,
            "md_steps": result.metadata.get("md_steps", 0),
            "scf_converged": result.metadata.get("scf_converged", False),
            "normal_end": result.metadata.get("normal_end", False),
            "warnings": result.warnings,
            "errors": result.errors,
        }

    def parse_ener(self, file_path: str) -> dict[str, Any]:
        """Parse a CP2K `.ener` file."""
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

        for raw_line in content.strip().splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or line.startswith("Step"):
                continue
            parts = line.split()
            if len(parts) < 7:
                continue
            try:
                data["steps"].append(int(parts[0]))
                data["times"].append(float(parts[1]))
                data["kinetic"].append(float(parts[2]))
                data["temperature"].append(float(parts[3]))
                data["potential"].append(float(parts[4]))
                data["cons_qty"].append(float(parts[5]))
                data["used_time"].append(float(parts[6]))
            except ValueError:
                continue

        if data["steps"]:
            data["md_steps"] = len(data["steps"])
            data["final_temperature"] = data["temperature"][-1]
            data["final_potential"] = data["potential"][-1]
            data["final_conserved_quantity"] = data["cons_qty"][-1]
            data["final_used_time"] = data["used_time"][-1]
        else:
            data["md_steps"] = 0
            data["final_temperature"] = None
            data["final_potential"] = None
            data["final_conserved_quantity"] = None
            data["final_used_time"] = None

        return data

    def parse_trajectory(self, file_path: str) -> list[dict[str, Any]]:
        """Parse a CP2K XYZ or EXTXYZ trajectory file."""
        content = self._read_file(file_path)
        frames: list[dict[str, Any]] = []
        lines = content.strip().splitlines()
        i = 0

        while i < len(lines):
            line = lines[i].strip()
            if not line:
                i += 1
                continue
            try:
                natoms = int(line)
            except ValueError:
                i += 1
                continue
            if i + 1 >= len(lines):
                break

            comment = lines[i + 1].strip()
            step = self._safe_int(self._match_first(comment, r"i\s*=\s*(\d+)", r"\bStep=(\d+)"))
            time_fs = self._safe_float(self._match_first(comment, r"time\s*=\s*([-\d.Ee+]+)", r"\bTime=([-\d.Ee+]+)"))
            energy = self._safe_float(self._match_first(comment, r"\bE\s*=\s*([-\d.Ee+]+)", r"\bEnergy=([-\d.Ee+]+)"))

            atoms = []
            for j in range(i + 2, min(i + 2 + natoms, len(lines))):
                parts = lines[j].split()
                if len(parts) < 4:
                    continue
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

    def parse_restart_metadata(self, file_path: str) -> dict[str, Any]:
        """Parse lightweight metadata from a CP2K restart file."""
        path = Path(file_path)
        content = self._read_file(file_path)
        return {
            "path": str(path),
            "file_name": path.name,
            "size_bytes": path.stat().st_size,
            "project_name": self._match_first(content, r"\bPROJECT(?:_NAME)?\s+([^\s]+)"),
            "run_type": self._match_first(content, r"\bRUN_TYPE\s+([A-Z_]+)"),
            "step_start_val": self._safe_int(self._match_first(content, r"\bSTEP_START_VAL\s+(\d+)")),
            "restart_file_name": self._match_first(content, r"\bRESTART_FILE_NAME\s+([^\s]+)"),
        }

    def parse_outputs(self, calc_dir: str, project: str | None = None) -> dict[str, Any]:
        """Parse a CP2K calculation directory and return a consolidated summary."""
        base = Path(calc_dir)
        if not base.is_dir():
            raise FileNotFoundError(f"Calculation directory not found: {calc_dir}")

        log_path = self._pick_file(base, project, ".log")
        ener_path = self._pick_file(base, project, ".ener")
        traj_path = self._pick_trajectory(base, project)
        restart_path = self._pick_restart(base, project)

        result: dict[str, Any] = {
            "status": "missing_outputs",
            "files": {
                "log": str(log_path) if log_path else None,
                "ener": str(ener_path) if ener_path else None,
                "trajectory": str(traj_path) if traj_path else None,
                "restart": str(restart_path) if restart_path else None,
            },
            "summary": {},
        }

        log_result = self.parse(str(log_path)) if log_path else None
        ener_result = self.parse_ener(str(ener_path)) if ener_path else None
        frames = self.parse_trajectory(str(traj_path)) if traj_path else []
        restart_meta = self.parse_restart_metadata(str(restart_path)) if restart_path else None

        last_frame = frames[-1] if frames else None
        summary = {
            "cp2k_version": log_result.metadata.get("cp2k_version") if log_result else None,
            "run_type": log_result.metadata.get("run_type") if log_result else None,
            "project": log_result.metadata.get("project_name") if log_result else (restart_meta or {}).get("project_name"),
            "scf_converged": log_result.metadata.get("scf_converged", False) if log_result else False,
            "normal_end": log_result.metadata.get("normal_end", False) if log_result else False,
            "abort": log_result.metadata.get("abort_detected", False) if log_result else False,
            "final_energy": log_result.final_energy if log_result else None,
            "md_steps": (ener_result or {}).get("md_steps") or (log_result.metadata.get("md_steps") if log_result else 0),
            "temperature": (ener_result or {}).get("final_temperature") or (log_result.metadata.get("final_temperature") if log_result else None),
            "conserved_quantity": (ener_result or {}).get("final_conserved_quantity"),
            "used_time": (ener_result or {}).get("final_used_time") or (log_result.metadata.get("used_time") if log_result else None),
            "last_frame": last_frame,
        }

        if any(path is not None for path in (log_path, ener_path, traj_path, restart_path)):
            result["status"] = "parsed"

        result["summary"] = summary
        if log_result:
            result["log"] = {
                "converged": log_result.converged,
                "job_type": log_result.job_type,
                "final_energy": log_result.final_energy,
                "warnings": log_result.warnings,
                "errors": log_result.errors,
                "metadata": log_result.metadata,
            }
        if ener_result:
            result["ener"] = ener_result
        if frames:
            result["trajectory"] = {
                "nframes": len(frames),
                "last_frame": last_frame,
            }
        if restart_meta:
            result["restart_metadata"] = restart_meta

        return result

    def _pick_file(self, base: Path, project: str | None, suffix: str) -> Path | None:
        if project:
            for candidate in (base / f"{project}{suffix}", base / f"{project}-1{suffix}"):
                if candidate.is_file():
                    return candidate
        candidates = sorted(base.glob(f"*{suffix}"))
        return candidates[0] if candidates else None

    def _pick_trajectory(self, base: Path, project: str | None) -> Path | None:
        if project:
            for candidate in (base / f"{project}-pos-1.xyz", base / f"{project}.xyz"):
                if candidate.is_file():
                    return candidate
        matches = sorted(base.glob("*-pos-*.xyz"))
        return matches[0] if matches else None

    def _pick_restart(self, base: Path, project: str | None) -> Path | None:
        if project:
            for candidate in (base / f"{project}-1.restart", base / f"{project}.restart"):
                if candidate.is_file():
                    return candidate
        matches = sorted(base.glob("*.restart"))
        return matches[0] if matches else None

    def _match_first(self, text: str, *patterns: str) -> str | None:
        for pattern in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE)
            if match:
                return match.group(1)
        return None

    def _safe_float(self, value: str | None) -> float | None:
        if value is None:
            return None
        return float(value)

    def _safe_int(self, value: str | None) -> int | None:
        if value is None:
            return None
        return int(value)
