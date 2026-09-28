#!/usr/bin/env python3
"""Parse LAMMPS outputs into an intake manifest for analysis-stage handoff.

This is a LAMMPS-specific output INTAKE adapter. It records log thermo
metadata, dump column/units/atom-identity/image-flag evidence, and data-file
topology provenance. It does NOT compute RDF, MSD, diffusion, or any property
claim; those belong to simflow-analysis-visualization.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
from lammps_parser import LAMMPSParser

_UNITS_RE = re.compile(r"^\s*units\s+(\S+)", re.MULTILINE)
_TIMESTEP_RE = re.compile(r"^\s*timestep\s+([\d.eE+-]+)", re.MULTILINE)
_ATOM_STYLE_RE = re.compile(r"^\s*atom_style\s+(\S+)", re.MULTILINE)


def _find_file(work_dir: Path, explicit: str | None, candidates: list[str]) -> Path | None:
    if explicit:
        p = Path(explicit)
        return p if p.is_absolute() else (work_dir / p)
    for name in candidates:
        candidate = work_dir / name
        if candidate.exists():
            return candidate
    return None


def parse_log(log_path: Path | None) -> dict[str, Any]:
    if log_path is None or not log_path.exists():
        return {"available": False, "path": str(log_path) if log_path else None}
    text = log_path.read_text(encoding="utf-8", errors="replace")
    units_match = _UNITS_RE.search(text)
    timestep_match = _TIMESTEP_RE.search(text)
    atom_style_match = _ATOM_STYLE_RE.search(text)

    thermo: dict[str, Any] = {}
    try:
        parsed = LAMMPSParser().parse(str(log_path))
        thermo = {
            "steps": parsed.metadata.get("thermo_steps"),
            "total_steps": parsed.metadata.get("total_steps"),
            "final_temp": parsed.metadata.get("final_temp"),
            "final_potential_energy": parsed.metadata.get("final_potential_energy"),
            "final_kinetic_energy": parsed.metadata.get("final_kinetic_energy"),
            "final_energy": parsed.final_energy,
            "timestep": parsed.parameters.get("timestep"),
            "converged": parsed.converged,
            "warnings": parsed.warnings,
            "errors": parsed.errors,
        }
    except Exception as exc:
        thermo = {"parse_error": str(exc)}

    return {
        "available": True,
        "path": str(log_path),
        "units_style": units_match.group(1) if units_match else None,
        "timestep_command": float(timestep_match.group(1)) if timestep_match else None,
        "atom_style": atom_style_match.group(1) if atom_style_match else None,
        "thermo": thermo,
    }


def parse_dump_header(dump_path: Path | None) -> dict[str, Any]:
    if dump_path is None or not dump_path.exists():
        return {"available": False, "path": str(dump_path) if dump_path else None}

    n_frames = 0
    n_atoms: int | None = None
    columns: list[str] | None = None
    box: list[list[float]] | None = None
    first_timestep: int | None = None
    scaled_coords = False
    image_flags = False
    atom_ids = False
    types = False

    try:
        with open(dump_path, "r", encoding="utf-8", errors="replace") as fh:
            line = fh.readline()
            while line:
                stripped = line.strip()
                if stripped == "ITEM: TIMESTEP":
                    n_frames += 1
                    if first_timestep is None:
                        try:
                            first_timestep = int(fh.readline().strip())
                        except ValueError:
                            first_timestep = None
                elif stripped.startswith("ITEM: NUMBER OF ATOMS"):
                    try:
                        n_atoms = int(fh.readline().strip())
                    except ValueError:
                        n_atoms = None
                elif stripped.startswith("ITEM: BOX BOUNDS"):
                    box = []
                    for _ in range(3):
                        parts = fh.readline().split()
                        if len(parts) >= 2:
                            box.append([float(parts[0]), float(parts[1])])
                elif stripped.startswith("ITEM: ATOMS"):
                    if columns is None:
                        col_line = stripped[len("ITEM: ATOMS"):].strip()
                        columns = col_line.split() if col_line else []
                        if columns:
                            image_flags = {"ix", "iy", "iz"}.issubset(set(columns))
                            scaled = any(c in {"xs", "ys", "zs"} for c in columns)
                            unscaled = any(c in {"x", "y", "z"} for c in columns)
                            scaled_coords = scaled and not unscaled
                            atom_ids = "id" in columns
                            types = "type" in columns
                    if n_atoms is not None:
                        for _ in range(n_atoms):
                            if not fh.readline():
                                break
                line = fh.readline()
    except OSError as exc:
        return {"available": True, "path": str(dump_path), "parse_error": str(exc)}

    return {
        "available": True,
        "path": str(dump_path),
        "frame_count": n_frames,
        "n_atoms": n_atoms,
        "first_timestep": first_timestep,
        "columns": columns,
        "has_image_flags": image_flags,
        "scaled_coords": scaled_coords,
        "has_atom_ids": atom_ids,
        "has_types": types,
        "box_bounds": box,
    }


def parse_data_header(data_path: Path | None) -> dict[str, Any]:
    if data_path is None or not data_path.exists():
        return {"available": False, "path": str(data_path) if data_path else None}
    masses: list[tuple[int, float]] = []
    n_atom_types: int | None = None
    n_atoms: int | None = None
    try:
        with open(data_path, "r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                s = line.strip()
                low = s.lower()
                if low.startswith("atoms"):
                    try:
                        n_atoms = int(s.split()[0])
                    except (ValueError, IndexError):
                        pass
                elif low.startswith("atom types"):
                    try:
                        n_atom_types = int(s.split()[0])
                    except (ValueError, IndexError):
                        pass
                elif low.startswith("masses"):
                    for _ in range(n_atom_types or 1024):
                        m_line = fh.readline()
                        if not m_line.strip():
                            break
                        parts = m_line.split()
                        if len(parts) >= 2:
                            try:
                                masses.append((int(parts[0]), float(parts[1])))
                            except ValueError:
                                break
                    break
    except OSError as exc:
        return {"available": True, "path": str(data_path), "parse_error": str(exc)}

    return {
        "available": True,
        "path": str(data_path),
        "n_atoms": n_atoms,
        "n_atom_types": n_atom_types,
        "masses": masses,
    }


def build_intake_manifest(
    *, log: dict, dump: dict, data: dict, work_dir: Path
) -> dict[str, Any]:
    missing: list[str] = []
    if not log.get("available"):
        missing.append("log.lammps")
    if not dump.get("available"):
        missing.append("dump trajectory")
    if not data.get("available"):
        missing.append("data/topology file")

    limitations: list[str] = []
    if dump.get("available"):
        if not dump.get("has_image_flags"):
            limitations.append(
                "dump lacks image flags (ix iy iz); wrapped coordinates may corrupt MSD/diffusion."
            )
        if not dump.get("has_atom_ids"):
            limitations.append("dump lacks atom ids; frame-to-frame atom matching is ambiguous.")
        if dump.get("scaled_coords"):
            limitations.append("dump uses scaled coordinates (xs ys zs); unwrap/convert before analysis.")
        if dump.get("frame_count") is not None and dump["frame_count"] < 10:
            limitations.append("dump has fewer than 10 frames; statistical claims should remain preliminary.")
    units_style = log.get("units_style")
    if units_style is None:
        limitations.append("units style not detected in log; unit conversion is ambiguous.")

    recommended_analysis: list[str] = []
    if dump.get("available") and dump.get("has_atom_ids"):
        recommended_analysis.append("md_structure")
        if dump.get("has_image_flags"):
            recommended_analysis.append("md_diffusion_transport")
        else:
            recommended_analysis.append("md_diffusion_transport_with_unwrapping")

    return {
        "manifest_type": "lammps_output_intake_manifest",
        "source_dir": str(work_dir),
        "source_files": {
            "log": log,
            "dump": dump,
            "data": data,
        },
        "units_style": units_style,
        "parser_helper": "parse_lammps_outputs.py (shared LAMMPSParser for log; lightweight dump/data header scan)",
        "missing_inputs": missing,
        "limitations": limitations,
        "recommended_analysis_family": recommended_analysis,
        "boundary": (
            "simflow-lammps records LAMMPS-specific output semantics only. Final "
            "RDF/MSD/diffusion/transport/elastic methods and claims belong to "
            "simflow-analysis-visualization."
        ),
    }


def parse_lammps_outputs(
    calc_dir: str,
    log_path: str | None = None,
    dump_path: str | None = None,
    data_path: str | None = None,
    report: str | None = None,
) -> dict[str, Any]:
    work_dir = Path(calc_dir).expanduser().resolve()
    log = parse_log(_find_file(work_dir, log_path, ["log.lammps", "lammps.log", "log.cite"]))
    dump = parse_dump_header(_find_file(work_dir, dump_path, ["dump.lammps", "dump.lammpstrj", "trajectory"]))
    data = parse_data_header(_find_file(work_dir, data_path, ["data.lammps", "data", "data.file"]))

    manifest = build_intake_manifest(log=log, dump=dump, data=data, work_dir=work_dir)

    result: dict[str, Any] = {
        "status": "success" if not manifest["missing_inputs"] else "needs_inputs",
        "intake_manifest": manifest,
    }
    if report:
        report_path = Path(report).expanduser()
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        result["report"] = str(report_path)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Parse LAMMPS outputs into an intake manifest")
    parser.add_argument("--calc-dir", required=True, help="Calculation directory to inspect")
    parser.add_argument("--log", default=None, help="Explicit LAMMPS log path (relative to calc-dir or absolute)")
    parser.add_argument("--dump", default=None, help="Explicit LAMMPS dump path (relative to calc-dir or absolute)")
    parser.add_argument("--data", default=None, help="Explicit LAMMPS data/topology path (relative to calc-dir or absolute)")
    parser.add_argument("--report", help="Optional JSON report path")
    args = parser.parse_args()

    try:
        result = parse_lammps_outputs(
            calc_dir=args.calc_dir,
            log_path=args.log,
            dump_path=args.dump,
            data_path=args.data,
            report=args.report,
        )
        print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    except Exception as exc:
        print(json.dumps({"status": "error", "message": str(exc)}, indent=2, ensure_ascii=False))
        sys.exit(1)


if __name__ == "__main__":
    main()
