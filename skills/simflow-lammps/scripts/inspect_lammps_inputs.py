#!/usr/bin/env python3
"""Inspect LAMMPS inputs and logs without executing LAMMPS."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

_simflow_root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_simflow_root))

from runtime.simflow_core.helper_evidence import build_helper_evidence, sha256_file, source_file_record
from runtime.simflow_core.script_contracts import add_helper_recording_args, maybe_record_helper_run
from runtime.simflow_helpers.adapters import adapter_capabilities


OFFICIAL_REFERENCES = {
    "commands": "https://docs.lammps.org/Commands.html",
    "units": "https://docs.lammps.org/units.html",
    "dump": "https://docs.lammps.org/dump.html",
    "compute_msd": "https://docs.lammps.org/compute_msd.html",
    "compute_rdf": "https://docs.lammps.org/compute_rdf.html",
    "fix_ave_time": "https://docs.lammps.org/fix_ave_time.html",
    "fix_nvt_npt_nph": "https://docs.lammps.org/fix_nh.html",
}

LOCAL_EXAMPLE_MOTIFS = {
    "lj_melt": {
        "example": "examples/melt/in.melt",
        "signals": ["lj/cut", "create_atoms", "nve"],
        "note": "Minimal Lennard-Jones melt pattern for smoke tests and reduced-unit examples.",
    },
    "diffusion_msd": {
        "example": "examples/DIFFUSE/in.msd.2d",
        "signals": ["compute msd", "slope(", "reset_timestep"],
        "note": "MSD/VACF diffusion examples emphasize equilibration and statistics.",
    },
    "rdf_adf": {
        "example": "examples/rdf-adf/in.spce",
        "signals": ["compute rdf", "compute adf", "fix ave/time"],
        "note": "RDF/ADF examples write averaged analysis data through fix ave/time.",
    },
    "rerun_analysis": {
        "example": "examples/rerun/in.rdf.rerun",
        "signals": ["rerun", "compute rdf", "fix ave/time"],
        "note": "Rerun examples separate trajectory production from post-processing.",
    },
    "viscosity_green_kubo": {
        "example": "examples/VISCOSITY/in.gk.2d",
        "signals": ["fix ave/correlate", "trap(", "pxy"],
        "note": "Transport examples require long sampling and statistical review.",
    },
    "elastic_modular": {
        "example": "examples/ELASTIC/in.elastic",
        "signals": ["include init.mod", "include potential.mod", "box/relax"],
        "note": "Elastic examples use include files and require potential/unit provenance.",
    },
}

POTENTIAL_SUFFIXES = (
    ".eam",
    ".alloy",
    ".tersoff",
    ".sw",
    ".reax",
    ".ffield",
    ".ff",
    ".table",
    ".kim",
    ".meam",
    ".library",
)
MLP_PAIR_STYLES = {
    "deepmd",
    "pace",
    "mace",
    "nequip",
    "allegro",
    "snap",
    "quip",
}
MLP_MODEL_SUFFIXES = (
    ".pb",
    ".pth",
    ".pt",
    ".model",
    ".model-lammps",
    ".yace",
    ".pace",
    ".yaml",
    ".yml",
    ".json",
    ".xml",
    ".quip",
    ".snapcoeff",
    ".snapparam",
)

TIMESTEP_REVIEW_LIMITS = {
    "real": 2.0,
    "metal": 0.005,
    "lj": 0.02,
}


def _strip_comment(line: str) -> str:
    return line.split("#", 1)[0].rstrip()


def _logical_lines(text: str) -> list[dict[str, Any]]:
    lines: list[dict[str, Any]] = []
    buffer = ""
    start_line = 0
    for line_no, raw in enumerate(text.splitlines(), start=1):
        code = _strip_comment(raw)
        if not code.strip() and not buffer:
            continue
        if not buffer:
            start_line = line_no
        if code.rstrip().endswith("&"):
            buffer += code.rstrip()[:-1] + " "
            continue
        logical = (buffer + code).strip()
        buffer = ""
        if logical:
            lines.append({"line": start_line, "text": logical})
    if buffer.strip():
        lines.append({"line": start_line, "text": buffer.strip()})
    return lines


def _parse_commands(text: str) -> list[dict[str, Any]]:
    commands = []
    for entry in _logical_lines(text):
        parts = entry["text"].split()
        if not parts:
            continue
        commands.append({
            "line": entry["line"],
            "name": parts[0].lower(),
            "args": parts[1:],
            "text": entry["text"],
        })
    return commands


def _commands_named(commands: list[dict[str, Any]], name: str) -> list[dict[str, Any]]:
    return [command for command in commands if command["name"] == name]


def _first_arg(commands: list[dict[str, Any]], name: str) -> str | None:
    matches = _commands_named(commands, name)
    if not matches or not matches[0]["args"]:
        return None
    return matches[0]["args"][0]


def _command_text(commands: list[dict[str, Any]]) -> str:
    return "\n".join(" ".join(command["text"].lower().split()) for command in commands)


def _style_from_fix(command: dict[str, Any]) -> str | None:
    args = command["args"]
    return args[2].lower() if len(args) >= 3 else None


def _style_from_compute(command: dict[str, Any]) -> str | None:
    args = command["args"]
    return args[2].lower() if len(args) >= 3 else None


def _potential_tokens(commands: list[dict[str, Any]]) -> list[str]:
    tokens: list[str] = []
    for command in _commands_named(commands, "pair_coeff"):
        for token in command["args"]:
            lowered = token.lower()
            if lowered in {"*", "none", "null"}:
                continue
            if lowered.endswith(POTENTIAL_SUFFIXES) or "/" in token or "\\" in token:
                tokens.append(token)
    return list(dict.fromkeys(tokens))


def _resolve_relative(input_script: Path, token: str) -> Path:
    candidate = Path(token).expanduser()
    if candidate.is_absolute():
        return candidate
    return input_script.parent / candidate


def _looks_like_file_token(token: str) -> bool:
    lowered = token.lower()
    if token in {"*", "none", "null"}:
        return False
    if token.startswith(("$", "{")):
        return False
    return lowered.endswith(MLP_MODEL_SUFFIXES) or "/" in token or "\\" in token


def _detected_mlp_pair_styles(commands: list[dict[str, Any]]) -> list[str]:
    styles: list[str] = []
    for command in _commands_named(commands, "pair_style"):
        for arg in command["args"]:
            style = arg.lower()
            if style in MLP_PAIR_STYLES:
                styles.append(style)
    for command in _commands_named(commands, "pair_coeff"):
        for arg in command["args"]:
            style = arg.lower()
            if style in MLP_PAIR_STYLES:
                styles.append(style)
    return list(dict.fromkeys(styles))


def _model_tokens_for_mlp(commands: list[dict[str, Any]], styles: list[str]) -> list[str]:
    if not styles:
        return []
    tokens: list[str] = []
    for command in _commands_named(commands, "pair_style"):
        seen_style = False
        for token in command["args"]:
            lowered = token.lower()
            if lowered in styles:
                seen_style = True
                continue
            if seen_style and _looks_like_file_token(token):
                tokens.append(token)
    for command in _commands_named(commands, "pair_coeff"):
        args = command["args"]
        for index, token in enumerate(args):
            lowered = token.lower()
            previous_is_style = index > 0 and args[index - 1].lower() in styles
            if _looks_like_file_token(token) or previous_is_style:
                if lowered not in MLP_PAIR_STYLES:
                    tokens.append(token)
    return list(dict.fromkeys(tokens))


def _file_provenance(input_script: Path, token: str, role: str) -> dict[str, Any]:
    path = _resolve_relative(input_script, token)
    return {
        "role": role,
        "token": token,
        "path": str(path),
        "present": path.exists(),
        "is_file": path.is_file(),
        "bytes": path.stat().st_size if path.is_file() else None,
        "sha256": sha256_file(path),
    }


def _lammps_mlp_deployment_manifest(input_script: Path, commands: list[dict[str, Any]]) -> dict[str, Any]:
    styles = _detected_mlp_pair_styles(commands)
    model_tokens = _model_tokens_for_mlp(commands, styles)
    model_files = [_file_provenance(input_script, token, "mlp_model_file") for token in model_tokens]
    return {
        "detected": bool(styles),
        "pair_styles": styles,
        "model_files": model_files,
        "handoff_to": "simflow-mlp" if styles else None,
        "claim_limits": [
            "Records LAMMPS MLP deployment provenance only.",
            "Does not judge model training quality, validation coverage, extrapolation safety, or production readiness.",
        ],
    }


def _dump_restart_manifest(input_script: Path, commands: list[dict[str, Any]]) -> dict[str, Any]:
    dumps = []
    for command in _commands_named(commands, "dump"):
        args = command["args"]
        output_token = args[4] if len(args) >= 5 else None
        dumps.append({
            "line": command["line"],
            "id": args[0] if len(args) >= 1 else None,
            "group": args[1] if len(args) >= 2 else None,
            "style": args[2] if len(args) >= 3 else None,
            "every": args[3] if len(args) >= 4 else None,
            "file": output_token,
            "path": str(_resolve_relative(input_script, output_token)) if output_token else None,
            "attributes": args[5:] if len(args) > 5 else [],
        })
    restarts = []
    for command in _commands_named(commands, "restart"):
        args = command["args"]
        restarts.append({
            "line": command["line"],
            "every": args[0] if args else None,
            "files": args[1:],
            "paths": [str(_resolve_relative(input_script, token)) for token in args[1:]],
        })
    for command in _commands_named(commands, "write_restart"):
        args = command["args"]
        restarts.append({
            "line": command["line"],
            "command": "write_restart",
            "files": args[:1],
            "paths": [str(_resolve_relative(input_script, token)) for token in args[:1]],
        })
    return {"dumps": dumps, "restarts": restarts}


def _resolve_data_file(input_script: Path, commands: list[dict[str, Any]], data_file: str | None) -> Path | None:
    if data_file:
        candidate = Path(data_file).expanduser()
        if candidate.is_absolute():
            return candidate
        return input_script.parent / candidate
    read_data = _commands_named(commands, "read_data")
    if not read_data or not read_data[0]["args"]:
        return None
    candidate = Path(read_data[0]["args"][0]).expanduser()
    if candidate.is_absolute():
        return candidate
    return input_script.parent / candidate


def _inspect_data_file(data_path: Path | None, atom_style: str | None) -> dict[str, Any]:
    if data_path is None:
        return {"path": None, "present": None, "warnings": []}
    if not data_path.exists():
        return {
            "path": str(data_path),
            "present": False,
            "warnings": [{"code": "missing_data_file", "message": f"LAMMPS data file not found: {data_path}"}],
        }

    text = data_path.read_text(encoding="utf-8", errors="replace")
    atom_count_match = re.search(r"^\s*(\d+)\s+atoms\b", text, re.MULTILINE)
    atoms_section = re.search(r"^\s*Atoms(?:\s*#\s*(\w+))?", text, re.MULTILINE)
    warnings = []
    if "Masses" not in text:
        warnings.append({"code": "missing_masses_section", "message": "Data file has no Masses section."})
    if not atoms_section:
        warnings.append({"code": "missing_atoms_section", "message": "Data file has no Atoms section."})
    declared_atom_style = atoms_section.group(1).lower() if atoms_section and atoms_section.group(1) else None
    if atom_style and declared_atom_style and atom_style.lower() != declared_atom_style:
        warnings.append({
            "code": "atom_style_mismatch",
            "message": f"Input uses atom_style {atom_style}, but data file Atoms section declares {declared_atom_style}.",
        })
    return {
        "path": str(data_path),
        "present": True,
        "atom_count": int(atom_count_match.group(1)) if atom_count_match else None,
        "atoms_section_style": declared_atom_style,
        "has_masses": "Masses" in text,
        "has_atoms": atoms_section is not None,
        "warnings": warnings,
    }


def _inspect_log_file(log_file: str | None) -> dict[str, Any] | None:
    if not log_file:
        return None
    path = Path(log_file).expanduser()
    if not path.exists():
        return {
            "path": str(path),
            "present": False,
            "warnings": [{"code": "missing_log_file", "message": f"LAMMPS log file not found: {path}"}],
        }
    text = path.read_text(encoding="utf-8", errors="replace")
    errors = re.findall(r"^ERROR[^\n]*", text, flags=re.MULTILINE)
    warnings = re.findall(r"^WARNING[^\n]*", text, flags=re.MULTILINE)
    thermo_rows = len(re.findall(r"^\s*\d+\s+[-+0-9.Ee]+\s+", text, flags=re.MULTILINE))
    loop_time_present = "Loop time" in text
    return {
        "path": str(path),
        "present": True,
        "errors": errors,
        "warnings": [{"code": "lammps_warning", "message": item} for item in warnings],
        "thermo_rows": thermo_rows,
        "loop_time_present": loop_time_present,
    }


def _matching_local_motifs(commands: list[dict[str, Any]]) -> list[dict[str, str]]:
    command_names = {command["name"] for command in commands}
    command_text = _command_text(commands)
    fix_styles = [style for command in _commands_named(commands, "fix") if (style := _style_from_fix(command))]
    compute_styles = [style for command in _commands_named(commands, "compute") if (style := _style_from_compute(command))]
    pair_style = _first_arg(commands, "pair_style") or ""

    motif_signals = {
        "lj_melt": "lj/cut" in pair_style and "create_atoms" in command_names and "nve" in fix_styles,
        "diffusion_msd": "msd" in compute_styles and "reset_timestep" in command_names and "slope(" in command_text,
        "rdf_adf": {"rdf", "adf"} & set(compute_styles) and "ave/time" in fix_styles,
        "rerun_analysis": "rerun" in command_names and "rdf" in compute_styles and "ave/time" in fix_styles,
        "viscosity_green_kubo": "ave/correlate" in fix_styles and ("trap(" in command_text or "pxy" in command_text),
        "elastic_modular": (
            any(command["name"] == "include" for command in commands)
            and ("box/relax" in fix_styles or "displace.mod" in command_text)
        ),
    }
    matches = []
    for motif, data in LOCAL_EXAMPLE_MOTIFS.items():
        if motif_signals.get(motif):
            matches.append({"motif": motif, "example": data["example"], "note": data["note"]})
    return matches


def _build_warnings(
    commands: list[dict[str, Any]],
    data_report: dict[str, Any],
    log_report: dict[str, Any] | None,
    *,
    force_field_source: str | None,
) -> list[dict[str, str]]:
    warnings: list[dict[str, str]] = []
    command_text = _command_text(commands)
    units = _first_arg(commands, "units")
    timestep = _first_arg(commands, "timestep")
    potential_files = _potential_tokens(commands)
    fix_styles = [style for command in _commands_named(commands, "fix") if (style := _style_from_fix(command))]
    compute_styles = [style for command in _commands_named(commands, "compute") if (style := _style_from_compute(command))]
    include_files = [command["args"][0] for command in _commands_named(commands, "include") if command["args"]]

    if potential_files and not force_field_source:
        warnings.append({
            "code": "force_field_source_not_documented",
            "message": "Potential or force-field files are referenced; record provenance before scientific use.",
        })
    for token in potential_files:
        if token.startswith(("/", "~")):
            warnings.append({
                "code": "private_or_absolute_potential_path",
                "message": f"Potential path may expose local/proprietary context: {token}",
            })

    if units and timestep:
        try:
            value = float(timestep)
        except ValueError:
            value = None
        limit = TIMESTEP_REVIEW_LIMITS.get(units.lower())
        if value is not None and limit is not None and value > limit:
            warnings.append({
                "code": "large_timestep_review",
                "message": f"timestep {value} is large for units {units}; review stability and force-field convention.",
            })

    if _commands_named(commands, "run") and not {"nve", "nvt", "npt", "nph", "langevin"} & set(fix_styles):
        warnings.append({
            "code": "no_integrator_or_thermostat_fix_detected",
            "message": "A run command is present, but no common integrator/thermostat fix was detected.",
        })

    if any("reax" in style or "comb" in style for style in [_first_arg(commands, "pair_style") or ""]):
        if not any(style and style.startswith("qeq") for style in fix_styles):
            warnings.append({
                "code": "charge_equilibration_review",
                "message": "Reactive/charge-transfer pair style detected; review whether qeq or equivalent charge handling is needed.",
            })

    dump_modify_sort = any(command["name"] == "dump_modify" and "sort" in command["args"] for command in commands)
    for command in _commands_named(commands, "dump"):
        args = command["args"]
        style = args[2].lower() if len(args) >= 3 else ""
        attributes = set(arg.lower() for arg in args[5:]) if len(args) > 5 else set()
        if style == "custom" and "id" not in attributes and not dump_modify_sort:
            warnings.append({
                "code": "dump_atom_identity_not_stable",
                "message": "Dump output lacks atom ids or dump_modify sort; frame-to-frame atom matching may be ambiguous.",
            })
        if style == "custom" and not ({"x", "y", "z"} & attributes or {"xu", "yu", "zu"} & attributes):
            warnings.append({
                "code": "dump_coordinates_not_detected",
                "message": "Custom dump does not visibly include coordinates; trajectory analysis may be limited.",
            })

    if "msd" in compute_styles and "reset_timestep" not in command_text:
        warnings.append({
            "code": "msd_time_origin_review",
            "message": "MSD analysis detected; record equilibration boundary and time-origin choice.",
        })
    for command in _commands_named(commands, "compute"):
        if _style_from_compute(command) != "rdf" or not command["args"]:
            continue
        compute_id = command["args"][0].lower()
        if f"c_{compute_id}" not in command_text:
            warnings.append({
                "code": "rdf_output_not_recorded",
                "message": f"compute {compute_id} rdf is defined but no c_{compute_id} output reference was detected.",
            })

    if include_files:
        warnings.append({
            "code": "include_files_not_expanded",
            "message": "LAMMPS include files were detected; inspect included files as separate artifacts.",
        })

    warnings.extend(data_report.get("warnings", []))
    if log_report:
        warnings.extend(log_report.get("warnings", []))
        for error in log_report.get("errors", []):
            warnings.append({"code": "lammps_log_error", "message": error})
    return warnings


def inspect_lammps_inputs(
    input_script: str,
    *,
    data_file: str | None = None,
    log_file: str | None = None,
    force_field_source: str | None = None,
) -> dict[str, Any]:
    """Inspect a LAMMPS input package without running it."""
    script_path = Path(input_script).expanduser()
    if not script_path.exists():
        return {
            "status": "error",
            "software": "lammps",
            "message": f"LAMMPS input script not found: {script_path}",
            "missing_required_files": [str(script_path)],
        }

    text = script_path.read_text(encoding="utf-8", errors="replace")
    commands = _parse_commands(text)
    command_names = [command["name"] for command in commands]
    command_text = _command_text(commands)
    compute_styles = [style for command in _commands_named(commands, "compute") if (style := _style_from_compute(command))]
    atom_style = _first_arg(commands, "atom_style")
    resolved_data_file = _resolve_data_file(script_path, commands, data_file)
    data_report = _inspect_data_file(resolved_data_file, atom_style)
    log_report = _inspect_log_file(log_file)

    has_system_definition = any(name in command_names for name in ("read_data", "read_restart")) or (
        "create_box" in command_names and "create_atoms" in command_names
    )
    has_operation = any(name in command_names for name in ("run", "minimize", "rerun"))
    required_checks = {
        "units": "units" in command_names,
        "atom_style": "atom_style" in command_names,
        "system_definition": has_system_definition,
        "pair_style": "pair_style" in command_names,
        "pair_coeff": "pair_coeff" in command_names,
        "operation": has_operation,
    }
    missing_required_items = [key for key, present in required_checks.items() if not present]
    missing_required_files = []
    if data_report.get("present") is False:
        missing_required_files.append(data_report["path"])
    if log_report and log_report.get("present") is False:
        missing_required_files.append(log_report["path"])

    warnings = _build_warnings(
        commands,
        data_report,
        log_report,
        force_field_source=force_field_source,
    )
    if missing_required_items:
        warnings.append({
            "code": "missing_required_input_items",
            "message": "Missing core input evidence: " + ", ".join(missing_required_items),
        })

    potential_files = _potential_tokens(commands)
    mlp_deployment_manifest = _lammps_mlp_deployment_manifest(script_path, commands)
    dump_restart_manifest = _dump_restart_manifest(script_path, commands)
    missing_mlp_models = [
        item for item in mlp_deployment_manifest["model_files"]
        if not item["present"]
    ]
    for item in missing_mlp_models:
        warnings.append({
            "code": "missing_mlp_model_file",
            "message": f"LAMMPS MLP deployment references missing model file: {item['token']}",
        })
    if mlp_deployment_manifest["detected"] and not force_field_source:
        warnings.append({
            "code": "mlp_deployment_source_not_documented",
            "message": "LAMMPS MLP pair style detected; record model training/provenance evidence before scientific claims.",
        })

    result = {
        "status": "error" if missing_required_files else ("warning" if warnings or missing_required_items else "pass"),
        "helper_evidence": build_helper_evidence(
            helper="lammps_inspect_inputs",
            capability="static_input_inspection",
            status="blocked" if missing_required_files else ("warning" if warnings or missing_required_items else "success"),
            stage="computation" if not log_file else "analysis_visualization",
            activity="static_input_inspection",
            evidence_role="lammps_input_inspection",
            source_files=[source_file_record(script_path)] + (
                [source_file_record(resolved_data_file, role="data_file")] if resolved_data_file else []
            ),
            actual_tool_used={"software": "lammps", "support_level": "helper_supported"},
            parser_status="parsed",
            claim_limits=[
                "Static inspection does not imply LAMMPS execution readiness.",
                "MLP deployment evidence records how a model is referenced by LAMMPS only.",
                "No MLP training quality, validation adequacy, or production readiness claim is made.",
            ],
            warnings=warnings,
            limitations=[
                "Input includes and variables are not fully expanded.",
                "No LAMMPS executable was called.",
            ],
            adapter_capabilities=adapter_capabilities("lammps"),
        ),
        "software": "lammps",
        "stage_hint": "computation" if not log_file else "analysis_visualization",
        "input_script": str(script_path),
        "data_file": data_report,
        "log_file": log_report,
        "commands_detected": sorted(set(command_names)),
        "required_checks": required_checks,
        "missing_required_items": missing_required_items,
        "missing_required_files": missing_required_files,
        "force_field_provenance": {
            "source": force_field_source,
            "potential_files": potential_files,
            "potential_file_records": [
                _file_provenance(script_path, token, "force_field_file")
                for token in potential_files
            ],
            "redistributed_by_simflow": False,
        },
        "lammps_mlp_deployment_manifest": mlp_deployment_manifest,
        "dump_restart_manifest": dump_restart_manifest,
        "claim_limits": [
            "LAMMPS inspection may support input/provenance claims only.",
            "MLP pair-style detection does not validate the referenced MLP model.",
        ],
        "intent_candidates": {
            "has_minimization": "minimize" in command_names,
            "has_md_run": "run" in command_names,
            "has_rerun_analysis": "rerun" in command_names,
            "has_msd": "msd" in compute_styles,
            "has_rdf": "rdf" in compute_styles,
        },
        "local_example_motifs": _matching_local_motifs(commands),
        "warnings": warnings,
        "recommended_artifacts": [
            "input_script",
            "data_file_or_structure_source",
            "force_field_provenance",
            "input_validation_report",
            "dry_run_report_before_execution",
            "credential_scan",
            "log_file_if_executed",
            "trajectory_or_analysis_outputs_if_claimed",
        ],
        "official_references": OFFICIAL_REFERENCES,
    }
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect LAMMPS inputs and logs without running LAMMPS")
    parser.add_argument("--input-script", required=True, help="LAMMPS input script, e.g. in.lammps")
    parser.add_argument("--data-file", default=None, help="Optional LAMMPS data file if not inferable from read_data")
    parser.add_argument("--log-file", default=None, help="Optional LAMMPS log file for post-run diagnostics")
    parser.add_argument("--force-field-source", default=None, help="Human-readable force-field provenance note")
    parser.add_argument("--output", default=None, help="Optional JSON report path")
    add_helper_recording_args(parser, default_stage="computation")
    args = parser.parse_args()

    result = inspect_lammps_inputs(
        args.input_script,
        data_file=args.data_file,
        log_file=args.log_file,
        force_field_source=args.force_field_source,
    )
    output_paths: list[str] = []
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
        output_paths.append(str(output_path))
        result["output_files"] = output_paths

    input_paths = [args.input_script]
    for optional_path in (args.data_file, args.log_file):
        if optional_path:
            input_paths.append(optional_path)

    result = maybe_record_helper_run(
        args=args,
        result=result,
        script_path=Path(__file__).resolve(),
        helper_name="lammps_inspect_inputs",
        software="lammps",
        input_paths=input_paths,
        output_paths=output_paths,
        metadata={"helper_result_status": result.get("status")},
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    if result.get("status") == "error":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
