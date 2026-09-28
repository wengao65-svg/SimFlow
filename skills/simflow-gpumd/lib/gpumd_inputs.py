"""Local GPUMD/NEP input rendering, parsing, and static validation."""

from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import Any

from pymatgen.core import Structure



TASK_ALIASES = {
    "minimize": "gpumd_minimize",
    "minimization": "gpumd_minimize",
    "relax": "gpumd_minimize",
    "relaxation": "gpumd_minimize",
    "md": "gpumd_md_nvt",
    "nvt": "gpumd_md_nvt",
    "nve": "gpumd_md_nve",
    "npt": "gpumd_md_npt",
    "gpumd": "gpumd_md_nvt",
    "gpumd_md": "gpumd_md_nvt",
    "gpumd_nvt": "gpumd_md_nvt",
    "gpumd_nve": "gpumd_md_nve",
    "gpumd_npt": "gpumd_md_npt",
    "nep": "nep_training",
    "nep_train": "nep_training",
    "nep_training": "nep_training",
    "train": "nep_training",
    "training": "nep_training",
    "prediction": "nep_prediction",
    "predict": "nep_prediction",
    "nep_prediction": "nep_prediction",
    "parse": "parse",
    "parser": "parse",
    "troubleshoot": "troubleshoot",
}

SUPPORTED_TASKS = {
    "gpumd_minimize",
    "gpumd_md_nve",
    "gpumd_md_nvt",
    "gpumd_md_npt",
    "nep_training",
    "nep_prediction",
    "parse",
    "troubleshoot",
}

def normalize_gpumd_task(task: str | None, *, software: str = "gpumd") -> str:
    """Normalize GPUMD/NEP task labels without defaulting unknown text silently."""
    if not task:
        return "nep_training" if software == "nep" else "gpumd_md_nvt"
    normalized = task.strip().lower().replace("-", "_").replace(" ", "_")
    normalized = TASK_ALIASES.get(normalized, normalized)
    if normalized not in SUPPORTED_TASKS:
        supported = ", ".join(sorted(SUPPORTED_TASKS))
        raise ValueError(f"Unknown GPUMD/NEP task: {task}. Supported values: {supported}.")
    return normalized


def parse_gpumd_command_text(content: str) -> list[dict[str, Any]]:
    """Parse keyword-style GPUMD/NEP command files."""
    commands: list[dict[str, Any]] = []
    for line_no, raw in enumerate(content.splitlines(), start=1):
        code = raw.split("#", 1)[0].strip()
        if not code:
            continue
        parts = code.split()
        commands.append({"line": line_no, "name": parts[0].lower(), "args": parts[1:], "text": code})
    return commands


def parse_run_in(path: str | Path) -> dict[str, Any]:
    candidate = Path(path)
    if not candidate.is_file():
        return {"status": "missing", "path": str(candidate), "commands": []}
    commands = parse_gpumd_command_text(candidate.read_text(encoding="utf-8", errors="replace"))
    names: dict[str, int] = {}
    references = []
    for command in commands:
        names[command["name"]] = names.get(command["name"], 0) + 1
        if command["name"] == "potential" and command["args"]:
            references.append(command["args"][0])
    return {
        "status": "parsed",
        "path": str(candidate),
        "command_count": len(commands),
        "commands": commands,
        "command_summary": names,
        "referenced_files": references,
    }


def parse_nep_in(path: str | Path) -> dict[str, Any]:
    candidate = Path(path)
    if not candidate.is_file():
        return {"status": "missing", "path": str(candidate), "commands": [], "keywords": {}}
    commands = parse_gpumd_command_text(candidate.read_text(encoding="utf-8", errors="replace"))
    keywords: dict[str, list[list[str]]] = {}
    for command in commands:
        keywords.setdefault(command["name"], []).append(command["args"])
    return {
        "status": "parsed",
        "path": str(candidate),
        "command_count": len(commands),
        "commands": commands,
        "keywords": keywords,
    }


def read_extxyz_summary(path: str | Path) -> dict[str, Any]:
    """Read a minimal extended XYZ summary without depending on GPUMD."""
    candidate = Path(path)
    if not candidate.is_file():
        return {"status": "missing", "path": str(candidate), "frames": 0, "elements": []}
    lines = candidate.read_text(encoding="utf-8", errors="replace").splitlines()
    index = 0
    frames = 0
    elements: dict[str, int] = {}
    warnings: list[dict[str, str]] = []
    metadata_keys: set[str] = set()
    while index < len(lines):
        raw_count = lines[index].strip()
        if not raw_count:
            index += 1
            continue
        try:
            natoms = int(raw_count)
        except ValueError:
            warnings.append({"code": "invalid_atom_count", "message": f"Line {index + 1} is not an atom count."})
            break
        if natoms < 1:
            warnings.append({"code": "invalid_atom_count", "message": f"Frame {frames + 1} has fewer than one atom."})
            break
        if index + natoms + 1 >= len(lines):
            warnings.append({"code": "truncated_frame", "message": f"Frame {frames + 1} is truncated."})
            break
        comment = lines[index + 1]
        for match in re.finditer(r"([A-Za-z_][A-Za-z0-9_]*)\s*=", comment):
            metadata_keys.add(match.group(1).lower())
        for atom_line in lines[index + 2:index + 2 + natoms]:
            parts = atom_line.split()
            if parts:
                elements[parts[0]] = elements.get(parts[0], 0) + 1
        frames += 1
        index += natoms + 2
    return {
        "status": "warning" if warnings else ("parsed" if frames else "malformed"),
        "path": str(candidate),
        "frames": frames,
        "elements": sorted(elements),
        "element_counts": elements,
        "metadata_keys": sorted(metadata_keys),
        "warnings": warnings,
    }


def write_model_xyz(structure_path: str | Path, output_path: str | Path, *, pbc: str = "T T T") -> dict[str, Any]:
    """Write a GPUMD-compatible model.xyz from a structure file."""
    structure = Structure.from_file(str(structure_path))
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    lattice_values = " ".join(f"{value:.10g}" for row in structure.lattice.matrix for value in row)
    lines = [
        str(len(structure)),
        f'pbc="{pbc}" lattice="{lattice_values}" properties=species:S:1:pos:R:3',
    ]
    element_counts: dict[str, int] = {}
    for site in structure:
        element = site.specie.symbol
        element_counts[element] = element_counts.get(element, 0) + 1
        x, y, z = site.coords
        lines.append(f"{element} {x:.10f} {y:.10f} {z:.10f}")
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {
        "path": str(output),
        "natoms": len(structure),
        "elements": sorted(element_counts),
        "element_counts": element_counts,
    }


def _existing_path(value: Any, source_dir: Path, output_dir: Path) -> Path | None:
    if not value:
        return None
    candidate = Path(str(value)).expanduser()
    for path in (
        candidate if candidate.is_absolute() else source_dir / candidate,
        output_dir / candidate,
    ):
        if path.is_file():
            return path.resolve()
    return None


def _copy_input_file(source: Path, output_dir: Path, name: str | None = None) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    target = output_dir / (name or source.name)
    if source.resolve() != target.resolve():
        shutil.copy2(source, target)
    return target


def _render_run_in(task: str, potential_name: str, params: dict[str, Any]) -> str:
    temperature = float(params.get("temperature", 300))
    timestep = float(params.get("timestep", 1.0))
    steps = int(params.get("steps", 1000))
    dump_interval = int(params.get("dump_thermo_interval", max(1, min(steps, 100))))
    lines = [f"potential {potential_name}"]
    if task == "gpumd_minimize":
        method = params.get("minimize_method", "fire")
        force_tolerance = params.get("force_tolerance", "1.0e-5")
        max_steps = int(params.get("max_minimize_steps", 1000))
        lines.append(f"minimize {method} {force_tolerance} {max_steps}")
    else:
        lines.extend([
            f"velocity {temperature:g}",
            f"time_step {timestep:g}",
        ])
        if task == "gpumd_md_nve":
            lines.append("ensemble nve")
        elif task == "gpumd_md_npt":
            pressure = float(params.get("pressure_gpa", 0.0))
            elastic = float(params.get("elastic_modulus_gpa", 100.0))
            lines.append(f"ensemble npt_ber {temperature:g} {temperature:g} 100 {pressure:g} {elastic:g} 1000")
        else:
            lines.append(f"ensemble nvt_ber {temperature:g} {temperature:g} 100")
        lines.extend([f"dump_thermo {dump_interval}", f"run {steps}"])
    return "\n".join(lines) + "\n"


def _nep_elements(params: dict[str, Any], train_path: Path | None) -> list[str]:
    raw = params.get("elements") or params.get("types")
    if isinstance(raw, str):
        return [item for item in raw.replace(",", " ").split() if item]
    if isinstance(raw, (list, tuple)):
        return [str(item) for item in raw if item]
    if train_path:
        summary = read_extxyz_summary(train_path)
        return list(summary.get("elements", []))
    return []


def _render_nep_in(task: str, params: dict[str, Any], elements: list[str]) -> str:
    version = int(params.get("version", 4))
    cutoff = params.get("cutoff", "8 4")
    n_max = params.get("n_max", "6 6")
    basis_size = params.get("basis_size", "6 6")
    l_max = params.get("l_max", "4 1")
    neuron = int(params.get("neuron", 30))
    generation = int(params.get("generation", 100000))
    prediction = 1 if task == "nep_prediction" else int(params.get("prediction", 0))
    lines = [
        f"type {len(elements)} {' '.join(elements)}",
        f"version {version}",
        f"cutoff {cutoff}",
        f"n_max {n_max}",
        f"basis_size {basis_size}",
        f"l_max {l_max}",
        f"neuron {neuron}",
        f"generation {generation}",
    ]
    if prediction:
        lines.append(f"prediction {prediction}")
    return "\n".join(lines) + "\n"


def generate_gpumd_inputs(
    structure_path: str | None,
    task: str,
    output_dir: str,
    *,
    params: dict[str, Any] | None = None,
    software: str = "gpumd",
    overwrite: bool = False,
) -> dict[str, Any]:
    """Generate bounded GPUMD/NEP inputs from explicit evidence."""
    params = dict(params or {})
    for key, value in params.items():
        values = value if isinstance(value, (list, tuple)) else [value]
        if any(isinstance(item, str) and ("\n" in item or "\r" in item) for item in values):
            raise ValueError(f"Parameter {key} must not contain newlines")
    out = Path(output_dir).expanduser().resolve()
    if ".simflow" in out.parts:
        raise ValueError("GPUMD inputs cannot be written under .simflow")
    source_dir = out.parent
    task_norm = normalize_gpumd_task(task, software=software)
    warnings: list[dict[str, str]] = []

    if task_norm.startswith("nep_"):
        train = _existing_path(params.get("train_xyz") or params.get("train_file"), source_dir, out)
        test = _existing_path(params.get("test_xyz") or params.get("test_file"), source_dir, out)
        model = _existing_path(params.get("nep_txt") or params.get("model_file"), source_dir, out)
        missing = []
        if train is None:
            missing.append("train_xyz")
        if task_norm == "nep_prediction" and model is None:
            missing.append("nep_txt")
        if missing:
            return {
                "status": "needs_inputs",
                "task": task_norm,
                "missing_inputs": missing,
                "message": "NEP helper input generation requires existing dataset/model evidence.",
            }
        assert train is not None
        elements = _nep_elements(params, train)
        if not elements:
            return {
                "status": "needs_inputs",
                "task": task_norm,
                "missing_inputs": ["elements"],
                "message": "Could not infer NEP type elements from parameters or train.xyz.",
            }
        targets = [out / "nep.in"] + [out / name for source, name in ((train, "train.xyz"), (test, "test.xyz"), (model, "nep.txt")) if source and source.resolve() != (out / name).resolve()]
        sources = {source.resolve() for source in (train, test, model) if source}
        if any(target.resolve() in sources for target in targets):
            raise ValueError("Output would overwrite another source input; choose a separate output directory")
        existing = [str(path) for path in targets if path.exists()]
        if existing and not overwrite:
            raise FileExistsError(f"Refusing to overwrite GPUMD/NEP inputs: {', '.join(existing)}")
        copied_train = _copy_input_file(train, out, "train.xyz")
        copied_test = _copy_input_file(test, out, "test.xyz") if test else None
        copied_model = _copy_input_file(model, out, "nep.txt") if model else None
        nep_in = out / "nep.in"
        nep_in.write_text(_render_nep_in(task_norm, params, elements), encoding="utf-8")
        generated = [nep_in, copied_train]
        if copied_test:
            generated.append(copied_test)
        if copied_model:
            generated.append(copied_model)
        return {
            "status": "success",
            "task": task_norm,
            "software": "nep",
            "files_generated": [str(path) for path in generated],
            "parameters": {
                "elements": elements,
                "train_xyz": str(copied_train),
                "test_xyz": str(copied_test) if copied_test else None,
                "nep_txt": str(copied_model) if copied_model else None,
            },
            "warnings": warnings,
        }

    potential = _existing_path(
        params.get("potential_file") or params.get("nep_model_file") or params.get("model_file"),
        source_dir,
        out,
    )
    missing = []
    if not structure_path:
        missing.append("structure")
    if potential is None:
        missing.append("potential_file")
    if missing:
        return {
            "status": "needs_inputs",
            "task": task_norm,
            "missing_inputs": missing,
            "message": "GPUMD input generation requires a structure and an existing potential/model file.",
        }
    assert structure_path is not None and potential is not None
    targets = [out / "run.in", out / "model.xyz"]
    if potential.resolve() != (out / potential.name).resolve():
        targets.append(out / potential.name)
    existing = [str(path) for path in targets if path.exists()]
    if existing and not overwrite:
        raise FileExistsError(f"Refusing to overwrite GPUMD/NEP inputs: {', '.join(existing)}")
    copied_potential = _copy_input_file(potential, out)
    model_summary = write_model_xyz(structure_path, out / "model.xyz", pbc=str(params.get("pbc", "T T T")))
    run_in = out / "run.in"
    run_in.write_text(_render_run_in(task_norm, copied_potential.name, params), encoding="utf-8")
    return {
        "status": "success",
        "task": task_norm,
        "software": "gpumd",
        "files_generated": [str(run_in), model_summary["path"], str(copied_potential)],
        "parameters": {
            "num_atoms": model_summary["natoms"],
            "elements": model_summary["elements"],
            "potential_file": str(copied_potential),
        },
        "warnings": warnings,
    }


def validate_gpumd_inputs(task: str, calc_dir: str, *, software: str = "gpumd") -> dict[str, Any]:
    """Validate GPUMD/NEP inputs without executing the engine."""
    task_norm = normalize_gpumd_task(task, software=software)
    base = Path(calc_dir).expanduser().resolve()
    checks: list[dict[str, Any]] = []
    detected: dict[str, Any] = {"task": task_norm, "calc_dir": str(base)}

    def check(name: str, passed: bool, message: str) -> None:
        checks.append({"check": name, "passed": passed, "message": message})

    if task_norm.startswith("nep_"):
        nep_in = parse_nep_in(base / "nep.in")
        train = read_extxyz_summary(base / "train.xyz")
        test = read_extxyz_summary(base / "test.xyz") if (base / "test.xyz").exists() else None
        detected.update({"nep_in": nep_in, "train_xyz": train, "test_xyz": test})
        check("nep_in_exists", nep_in["status"] == "parsed", "nep.in found." if nep_in["status"] == "parsed" else "nep.in is missing.")
        keywords = nep_in.get("keywords", {})
        check("type_keyword", "type" in keywords, "NEP type keyword found." if "type" in keywords else "NEP type keyword is missing.")
        check("train_xyz_exists", train["status"] in {"parsed", "warning"}, "train.xyz found." if train["frames"] else "train.xyz is missing or malformed.")
        if task_norm == "nep_prediction":
            check("nep_txt_exists", (base / "nep.txt").is_file(), "nep.txt found." if (base / "nep.txt").is_file() else "nep.txt is required for prediction mode.")
    else:
        run_in = parse_run_in(base / "run.in")
        model = read_extxyz_summary(base / "model.xyz")
        detected.update({"run_in": run_in, "model_xyz": model})
        check("run_in_exists", run_in["status"] == "parsed", "run.in found." if run_in["status"] == "parsed" else "run.in is missing.")
        check("model_xyz_exists", model["status"] in {"parsed", "warning"}, "model.xyz found." if model["frames"] else "model.xyz is missing or malformed.")
        command_names = run_in.get("command_summary", {})
        check("potential_command", "potential" in command_names, "potential command found." if "potential" in command_names else "run.in is missing a potential command.")
        for ref in run_in.get("referenced_files", []):
            ref_path = base / ref
            check(f"referenced_file:{ref}", ref_path.is_file(), f"Referenced file found: {ref}" if ref_path.is_file() else f"Referenced file is missing: {ref}")
        if task_norm != "gpumd_minimize":
            check("run_command", "run" in command_names, "run command found." if "run" in command_names else "run.in is missing a run command.")

    failed = [item for item in checks if not item["passed"]]
    status = "fail" if failed else "pass"
    has_warnings = bool((detected.get("train_xyz") or {}).get("warnings", [])) or bool(
        (detected.get("model_xyz") or {}).get("warnings", [])
    )
    if not failed and has_warnings:
        status = "warning"
    return {
        "status": status,
        "valid": not failed,
        "task": task_norm,
        "software": "nep" if task_norm.startswith("nep_") else "gpumd",
        "calc_dir": str(base),
        "checks": checks,
        "detected": detected,
        "claim_limits": [
            "Input validation does not execute GPUMD/NEP.",
            "Validation does not certify model quality, transport properties, or production readiness.",
        ],
    }
