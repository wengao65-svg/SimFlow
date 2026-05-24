"""VASP input and dependency validation helpers."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .vasp_potcar import validate_potcar


_SCF_DEPENDENT_TASKS = {"dos", "band", "bands", "band_structure"}


def _read_kpoints_mode(kpoints_path: Path) -> str:
    if not kpoints_path.is_file():
        return "missing"
    lines = [line.strip() for line in kpoints_path.read_text(errors="replace").splitlines() if line.strip()]
    text = "\n".join(lines).lower()
    if "line-mode" in text or (len(lines) >= 3 and lines[2].lower().startswith("line")):
        return "line"
    if any(token in text for token in ("gamma", "monkhorst", "automatic")):
        return "mesh"
    return "unknown"


def _read_incar_tags(incar_path: Path) -> dict[str, str]:
    tags: dict[str, str] = {}
    if not incar_path.is_file():
        return tags
    for raw in incar_path.read_text(errors="replace").splitlines():
        line = raw.split("#", 1)[0].split("!", 1)[0].strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        tags[key.strip().upper()] = value.strip()
    return tags


def _read_poscar_summary(poscar_path: Path) -> dict[str, Any]:
    if not poscar_path.is_file():
        return {"exists": False}
    lines = [line.strip() for line in poscar_path.read_text(errors="replace").splitlines() if line.strip()]
    if len(lines) < 8:
        return {"exists": True, "valid": False, "message": "POSCAR too short"}
    species = lines[5].split()
    counts = []
    try:
        counts = [int(x) for x in lines[6].split()]
    except ValueError:
        pass
    lattice_lengths = []
    for idx in (2, 3, 4):
        try:
            vec = [float(x) for x in lines[idx].split()[:3]]
            lattice_lengths.append(sum(x * x for x in vec) ** 0.5)
        except ValueError:
            lattice_lengths.append(0.0)
    return {
        "exists": True,
        "valid": bool(species and counts and len(species) == len(counts)),
        "species": species,
        "counts": counts,
        "lattice_lengths": lattice_lengths,
    }


def _validate_structure_check_task(task_norm: str, base: Path) -> dict[str, Any]:
    checks = []
    summary = _read_poscar_summary(base / "POSCAR")
    checks.append({
        "check": "poscar_exists",
        "passed": summary.get("exists", False),
        "message": "POSCAR found" if summary.get("exists") else "POSCAR missing",
    })
    checks.append({
        "check": "poscar_species_counts",
        "passed": summary.get("valid", False),
        "message": "POSCAR species/count lines are consistent" if summary.get("valid") else "POSCAR species/count lines need review",
        "metadata": {k: summary.get(k) for k in ("species", "counts") if k in summary},
    })
    if task_norm == "surface_check":
        lengths = summary.get("lattice_lengths") or []
        vacuum_like = len(lengths) == 3 and lengths[2] > 1.2 * max(lengths[0], lengths[1])
        checks.append({
            "check": "surface_vacuum_heuristic",
            "passed": vacuum_like,
            "message": "Cell c-axis is vacuum-like by a simple length heuristic" if vacuum_like else "Surface slab may need vacuum/separation review",
        })
    elif task_norm == "adsorption_check":
        species = summary.get("species") or []
        checks.append({
            "check": "adsorption_species_diversity",
            "passed": len(species) >= 2,
            "message": "Multiple species present for adsorption model" if len(species) >= 2 else "Adsorption model usually contains slab and adsorbate species",
        })
    elif task_norm == "defect_check":
        checks.append({
            "check": "defect_supercell_review",
            "passed": True,
            "message": "Defect charge state, image separation, and reference pristine cell require user/workflow review",
        })
    return {
        "status": "pass" if all(c["passed"] for c in checks) else "fail",
        "valid": all(c["passed"] for c in checks),
        "task": task_norm,
        "calc_dir": str(base),
        "checks": checks,
    }


def validate_potcar_metadata(poscar: str, potcar: str) -> dict[str, Any]:
    """Validate POTCAR metadata without returning POTCAR content."""
    result = validate_potcar(poscar, potcar)
    return {
        "valid": result.get("valid", False),
        "poscar_elements": result.get("poscar_elements", []),
        "potcar_elements": result.get("potcar_elements", []),
        "message": result.get("message"),
        "content_included": False,
    }


def validate_vasp_dependencies(task: str, calc_dir: str) -> dict[str, Any]:
    """Check common predecessor files for post-SCF tasks."""
    task_norm = task.lower()
    base = Path(calc_dir)
    checks = []

    if task_norm in _SCF_DEPENDENT_TASKS:
        chgcar = base / "CHGCAR"
        checks.append({
            "check": "prior_scf_chgcar",
            "passed": chgcar.is_file(),
            "message": "CHGCAR available from prior SCF" if chgcar.is_file() else "DOS/band tasks require prior static SCF CHGCAR",
        })

    if task_norm in {"neb", "neb_basic"}:
        image_dirs = sorted(p for p in base.iterdir() if p.is_dir() and re.fullmatch(r"\d{2}", p.name)) if base.exists() else []
        checks.append({
            "check": "neb_images",
            "passed": len(image_dirs) >= 2,
            "message": f"{len(image_dirs)} NEB image directories found",
        })

    return {"valid": all(c["passed"] for c in checks), "checks": checks}


def validate_vasp_inputs(task: str, calc_dir: str) -> dict[str, Any]:
    """Validate a VASP calculation directory for common task-level mistakes."""
    base = Path(calc_dir)
    task_norm = task.lower()
    checks = []

    if task_norm in {"surface_check", "adsorption_check", "defect_check"}:
        return _validate_structure_check_task(task_norm, base)

    required = ("INCAR", "KPOINTS") if task_norm in {"neb", "neb_basic"} else ("POSCAR", "INCAR", "KPOINTS")
    for name in required:
        path = base / name
        checks.append({
            "check": f"{name.lower()}_exists",
            "passed": path.is_file(),
            "message": f"{name} found" if path.is_file() else f"{name} missing",
        })

    poscar = base / "POSCAR"
    potcar = base / "POTCAR"
    if task_norm in {"neb", "neb_basic"} and potcar.is_file() and not poscar.is_file():
        checks.append({
            "check": "potcar_metadata",
            "passed": True,
            "message": "POTCAR present; NEB image POSCAR order must be checked per image by the workflow",
            "metadata": {"content_included": False},
        })
    elif poscar.is_file() and potcar.is_file():
        meta = validate_potcar_metadata(str(poscar), str(potcar))
        checks.append({
            "check": "potcar_element_order",
            "passed": bool(meta["valid"]),
            "message": meta["message"],
            "metadata": meta,
        })
    else:
        checks.append({
            "check": "potcar_metadata",
            "passed": False,
            "message": "POTCAR missing or POSCAR missing; SimFlow will not generate or distribute POTCAR content",
        })

    kpoints_mode = _read_kpoints_mode(base / "KPOINTS")
    if task_norm in {"band", "bands", "band_structure"}:
        passed = kpoints_mode == "line"
        message = "Band structure KPOINTS uses line mode" if passed else "Band structure normally needs line-mode KPOINTS"
    elif task_norm in {"relax", "static", "scf", "dos", "aimd", "md"}:
        passed = kpoints_mode in {"mesh", "unknown"}
        message = "KPOINTS mode compatible with mesh-style task" if passed else "This task normally uses mesh KPOINTS, not line-mode"
    else:
        passed = kpoints_mode != "missing"
        message = f"KPOINTS mode: {kpoints_mode}"
    checks.append({"check": "kpoints_task_match", "passed": passed, "message": message, "mode": kpoints_mode})

    incar_tags = _read_incar_tags(base / "INCAR")
    if task_norm in {"aimd", "md"}:
        checks.append({
            "check": "aimd_incar_tags",
            "passed": incar_tags.get("IBRION") == "0" and int(float(incar_tags.get("NSW", "0"))) > 0,
            "message": "AIMD INCAR has IBRION=0 and NSW>0",
        })

    deps = validate_vasp_dependencies(task_norm, calc_dir)
    checks.extend(deps["checks"])

    return {
        "status": "pass" if all(c["passed"] for c in checks) else "fail",
        "valid": all(c["passed"] for c in checks),
        "task": task,
        "calc_dir": str(base),
        "checks": checks,
    }
