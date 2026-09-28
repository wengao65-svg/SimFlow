"""Restricted POTCAR selection, materialization, and metadata helpers.

ASE supplies only the setup-profile tables used to resolve deterministic
dataset names. SimFlow owns library discovery, restricted file access,
concatenation, validation, hashing, and destination policy.
"""

from __future__ import annotations

import hashlib
import os
import re
import shutil
import tempfile
from pathlib import Path
from typing import Any, List, Optional


SUPPORTED_POTCAR_SETUP_PROFILES = ("minimal", "recommended", "gw")
_DATASET_RE = re.compile(r"^([A-Z][a-z]?)(?:_[A-Za-z0-9][A-Za-z0-9_.-]*)?$")
_SUFFIX_RE = re.compile(r"^(?:|_[A-Za-z0-9][A-Za-z0-9_.-]*)$")
_FLAVOR_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")


def get_potcar_path() -> Optional[str]:
    """Get the configured pseudopotential library root."""
    return os.environ.get("SIMFLOW_VASP_POTCAR_PATH")


def get_potcar_flavor() -> str:
    """Get the configured POTCAR functional flavor."""
    return os.environ.get("SIMFLOW_VASP_POTCAR_FLAVOR", "PBE")


def read_poscar_species(poscar_path: str) -> List[str]:
    """Read a VASP5 POSCAR and return species in file order."""
    with open(poscar_path, "r", encoding="utf-8") as handle:
        lines = [line.strip() for line in handle.readlines()]

    if len(lines) < 6:
        raise ValueError(f"POSCAR too short ({len(lines)} lines)")

    parts = lines[5].split()
    try:
        [int(value) for value in parts]
    except ValueError:
        return parts
    raise ValueError(
        "VASP4 POSCAR detected (no species line). "
        "Cannot determine element order. Add species names on line 6."
    )


def _setup_error(reason_code: str, message: str, **metadata: Any) -> dict[str, Any]:
    return {
        "status": "error",
        "reason_code": reason_code,
        "message": message,
        "content_included": False,
        **metadata,
    }


def resolve_potcar_setups(
    elements: list[str],
    setups: str | dict[str, str] | None = None,
) -> dict[str, Any]:
    """Resolve fixed ASE-style setup profiles into exact dataset names.

    Only ``minimal``, ``recommended``, and ``gw`` are accepted. ASE provides
    the profile tables; SimFlow performs the merge and never asks ASE to find,
    read, or construct POTCAR files.
    """
    base = "minimal"
    overrides: dict[str, str] = {}
    if setups is None:
        pass
    elif isinstance(setups, str):
        base = setups.strip().lower()
    elif isinstance(setups, dict):
        raw_base = setups.get("base", "minimal")
        if not isinstance(raw_base, str):
            return _setup_error(
                "invalid_potcar_setup_profile",
                "potcar_setups.base must be a profile name.",
            )
        base = raw_base.strip().lower()
        for key, value in setups.items():
            if key == "base":
                continue
            if isinstance(key, int) or (isinstance(key, str) and key.isdigit()):
                return _setup_error(
                    "atom_index_setup_unsupported",
                    "Per-atom POTCAR setups are not supported; use element-level overrides.",
                )
            if not isinstance(key, str) or key not in elements:
                return _setup_error(
                    "potcar_setup_unknown_element",
                    "POTCAR setup overrides must name species present in POSCAR.",
                    element=str(key),
                )
            if not isinstance(value, str) or not _SUFFIX_RE.fullmatch(value):
                return _setup_error(
                    "invalid_potcar_setup_suffix",
                    "Element setup overrides must be empty or an ASE-style suffix such as _pv.",
                    element=key,
                )
            overrides[key] = value
    else:
        return _setup_error(
            "invalid_potcar_setups",
            "potcar_setups must be a supported profile name, a mapping, or null.",
        )

    if base not in SUPPORTED_POTCAR_SETUP_PROFILES:
        return _setup_error(
            "unsupported_potcar_setup_profile",
            "Unsupported POTCAR setup profile.",
            profile=base,
            supported_profiles=list(SUPPORTED_POTCAR_SETUP_PROFILES),
        )

    try:
        import ase
        from ase.calculators.vasp.setups import get_default_setups
    except ImportError:
        return _setup_error(
            "potcar_setup_dependency_missing",
            "ASE is required to resolve POTCAR setup profiles.",
        )

    tables = get_default_setups()
    if base not in tables or not isinstance(tables[base], dict):
        return _setup_error(
            "potcar_setup_table_unavailable",
            "The installed ASE version does not provide the required setup table.",
            profile=base,
        )

    suffixes = dict(tables[base])
    suffixes.update(overrides)
    resolved = [f"{element}{suffixes.get(element, '')}" for element in elements]
    return {
        "status": "success",
        "profile": base,
        "overrides": overrides,
        "resolved_datasets": resolved,
        "ase_version": getattr(ase, "__version__", "unknown"),
        "content_included": False,
    }


def _contains_dataset_dirs(path: Path) -> bool:
    try:
        return any(child.is_dir() and (child / "POTCAR").is_file() for child in path.iterdir())
    except OSError:
        return False


def _resolve_flavor_dir(potcar_root: str, flavor: str) -> Optional[Path]:
    root = Path(potcar_root).expanduser().resolve()
    nested = root / flavor
    if nested.is_dir() and _contains_dataset_dirs(nested):
        return nested.resolve()
    if root.is_dir() and _contains_dataset_dirs(root):
        return root
    return None


def _list_available_elements(potcar_root: str, flavor: str) -> List[str]:
    """List available dataset directory names without exposing source paths."""
    flavor_dir = _resolve_flavor_dir(potcar_root, flavor)
    if flavor_dir is None:
        return []
    return sorted(
        child.name
        for child in flavor_dir.iterdir()
        if child.is_dir() and (child / "POTCAR").is_file()
    )


def _available_datasets_for_element(flavor_dir: Path, element: str) -> list[str]:
    return sorted(
        child.name
        for child in flavor_dir.iterdir()
        if child.is_dir()
        and (child / "POTCAR").is_file()
        and (child.name == element or child.name.startswith(f"{element}_"))
    )


def _find_element_potcar(
    potcar_root: str,
    flavor: str,
    element: str,
    dataset: str | None = None,
) -> Optional[Path]:
    """Return only the exact requested dataset POTCAR; never use wildcard fallback."""
    flavor_dir = _resolve_flavor_dir(potcar_root, flavor)
    selected = dataset or element
    if flavor_dir is None or not _DATASET_RE.fullmatch(selected):
        return None
    candidate = flavor_dir / selected / "POTCAR"
    if not candidate.is_file():
        return None
    resolved = candidate.resolve()
    try:
        resolved.relative_to(flavor_dir)
    except ValueError:
        return None
    return resolved


def _sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _extract_potcar_datasets(potcar_path: str | Path) -> List[str]:
    """Extract complete dataset labels such as Fe, Fe_pv, and Fe_sv."""
    datasets: list[str] = []
    with Path(potcar_path).open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            parts = line.strip().split()
            if len(parts) < 2 or not parts[0].startswith("PAW"):
                continue
            dataset = parts[1]
            if _DATASET_RE.fullmatch(dataset):
                datasets.append(dataset)
    return datasets


def _extract_potcar_elements(potcar_path: str) -> List[str]:
    """Extract base element symbols from POTCAR dataset headers."""
    elements = []
    for dataset in _extract_potcar_datasets(potcar_path):
        match = _DATASET_RE.fullmatch(dataset)
        if match:
            elements.append(match.group(1))
    return elements


def validate_potcar(
    poscar_path: str,
    potcar_path: str,
    expected_datasets: list[str] | None = None,
) -> dict[str, Any]:
    """Validate POTCAR element order and optional exact dataset sequence."""
    try:
        poscar_elements = read_poscar_species(poscar_path)
    except (FileNotFoundError, ValueError) as error:
        return {
            "valid": False,
            "reason_code": "poscar_unreadable",
            "message": f"Cannot read POSCAR: {error}",
            "content_included": False,
        }

    path = Path(potcar_path)
    if not path.is_file():
        return {
            "valid": False,
            "reason_code": "potcar_missing",
            "message": "POTCAR not found",
            "content_included": False,
        }

    datasets = _extract_potcar_datasets(path)
    potcar_elements = _extract_potcar_elements(str(path))
    element_order_valid = poscar_elements == potcar_elements
    dataset_sequence_valid = expected_datasets is None or datasets == expected_datasets
    valid = element_order_valid and dataset_sequence_valid and bool(datasets)
    if not element_order_valid:
        reason_code = "potcar_element_order_mismatch"
        message = "POTCAR element order does not match POSCAR."
    elif not dataset_sequence_valid:
        reason_code = "existing_potcar_dataset_mismatch"
        message = "Existing POTCAR dataset sequence does not match the resolved setup selection."
    elif not datasets:
        reason_code = "potcar_headers_unrecognized"
        message = "POTCAR dataset headers could not be recognized."
    else:
        reason_code = None
        message = "POTCAR element and dataset sequence validation passed."
    return {
        "valid": valid,
        "reason_code": reason_code,
        "poscar_elements": poscar_elements,
        "potcar_elements": potcar_elements,
        "potcar_datasets": datasets,
        "expected_datasets": expected_datasets,
        "element_order_valid": element_order_valid,
        "dataset_sequence_valid": dataset_sequence_valid,
        "size_bytes": path.stat().st_size,
        "sha256": _sha256_file(path),
        "message": message,
        "content_included": False,
    }


def _materialization_metadata(
    status: str,
    elements: list[str],
    selection: dict[str, Any] | None,
    validation: dict[str, Any] | None,
    *,
    reason_code: str | None = None,
    message: str,
    content_materialized: bool,
    available_datasets: dict[str, list[str]] | None = None,
) -> dict[str, Any]:
    result = {
        "status": status,
        "reason_code": reason_code,
        "message": message,
        "elements": elements,
        "resolved_datasets": (selection or {}).get("resolved_datasets", []),
        "selection_policy": selection,
        "validation": validation,
        "size_bytes": (validation or {}).get("size_bytes"),
        "sha256": (validation or {}).get("sha256"),
        "restricted": True,
        "content_materialized": content_materialized,
        "content_included": False,
        "output_name": "POTCAR",
    }
    if available_datasets:
        result["available_datasets"] = available_datasets
    return result


def _validate_output_location(output_path: Path, project_root: str | None) -> Optional[dict[str, Any]]:
    resolved = output_path.expanduser().resolve()
    if output_path.name != "POTCAR":
        return _setup_error(
            "restricted_potcar_output_name",
            "Restricted POTCAR materialization requires the output name POTCAR.",
        )
    if ".simflow" in resolved.parts:
        return _setup_error(
            "restricted_potcar_output_location",
            "POTCAR cannot be materialized inside .simflow.",
        )
    if project_root:
        root = Path(project_root).expanduser().resolve()
        try:
            resolved.relative_to(root)
        except ValueError:
            return _setup_error(
                "restricted_potcar_output_location",
                "POTCAR output must remain inside project_root.",
            )
        if resolved.parent == root:
            return _setup_error(
                "restricted_potcar_output_location",
                "POTCAR cannot be materialized at project_root.",
            )
    return None


def generate_potcar(
    poscar_path: str,
    output_path: str,
    potcar_root: str | None = None,
    flavor: str | None = None,
    setups: str | dict[str, str] | None = None,
    use_vaspkit: bool = False,
    project_root: str | None = None,
) -> dict[str, Any]:
    """Materialize a restricted POTCAR without exposing its contents."""
    try:
        elements = read_poscar_species(poscar_path)
    except (FileNotFoundError, ValueError) as error:
        return _materialization_metadata(
            "error",
            [],
            None,
            None,
            reason_code="poscar_unreadable",
            message=f"Cannot read POSCAR: {error}",
            content_materialized=False,
        )

    root = potcar_root or get_potcar_path()
    selected_flavor = flavor or get_potcar_flavor()
    output = Path(output_path)

    # Existing POTCAR files must match the setup policy for this request, even
    # when no library access is needed to reuse the file.
    if output.is_file():
        location_error = _validate_output_location(output, project_root)
        if location_error:
            return _materialization_metadata(
                "error",
                elements,
                None,
                None,
                reason_code=location_error["reason_code"],
                message=location_error["message"],
                content_materialized=False,
            )
        selection = resolve_potcar_setups(elements, setups)
        if selection["status"] != "success":
            return _materialization_metadata(
                "error",
                elements,
                selection,
                None,
                reason_code=selection["reason_code"],
                message=selection["message"],
                content_materialized=False,
            )
        validation = validate_potcar(
            poscar_path,
            str(output),
            expected_datasets=selection["resolved_datasets"],
        )
        return _materialization_metadata(
            "existing" if validation["valid"] else "error",
            elements,
            selection,
            validation,
            reason_code=None if validation["valid"] else validation.get("reason_code"),
            message=validation["message"],
            content_materialized=False,
        )

    if not root:
        selection = resolve_potcar_setups(elements, setups) if setups is not None else None
        if selection is not None and selection["status"] != "success":
            return _materialization_metadata(
                "error",
                elements,
                selection,
                None,
                reason_code=selection["reason_code"],
                message=selection["message"],
                content_materialized=False,
            )
        return _materialization_metadata(
            "unavailable",
            elements,
            selection,
            None,
            reason_code="potcar_library_not_configured",
            message="No POTCAR library is configured; restricted materialization was not attempted.",
            content_materialized=False,
        )

    if not isinstance(selected_flavor, str) or not _FLAVOR_RE.fullmatch(selected_flavor):
        return _materialization_metadata(
            "error",
            elements,
            None,
            None,
            reason_code="invalid_potcar_flavor",
            message="POTCAR flavor must be a single library directory name.",
            content_materialized=False,
        )

    location_error = _validate_output_location(output, project_root)
    if location_error:
        return _materialization_metadata(
            "error",
            elements,
            None,
            None,
            reason_code=location_error["reason_code"],
            message=location_error["message"],
            content_materialized=False,
        )

    selection = resolve_potcar_setups(elements, setups)
    if selection["status"] != "success":
        return _materialization_metadata(
            "error",
            elements,
            selection,
            None,
            reason_code=selection["reason_code"],
            message=selection["message"],
            content_materialized=False,
        )

    flavor_dir = _resolve_flavor_dir(root, selected_flavor)
    if flavor_dir is None:
        return _materialization_metadata(
            "error",
            elements,
            selection,
            None,
            reason_code="potcar_flavor_unavailable",
            message="The configured POTCAR library does not contain the requested flavor.",
            content_materialized=False,
        )

    source_files: list[Path] = []
    missing: dict[str, list[str]] = {}
    for element, dataset in zip(elements, selection["resolved_datasets"]):
        source = _find_element_potcar(root, selected_flavor, element, dataset=dataset)
        if source is None:
            missing[element] = _available_datasets_for_element(flavor_dir, element)
            continue
        source_validation = _extract_potcar_datasets(source)
        if source_validation != [dataset]:
            return _materialization_metadata(
                "error",
                elements,
                selection,
                None,
                reason_code="potcar_library_dataset_mismatch",
                message="A selected library POTCAR does not match its dataset directory.",
                content_materialized=False,
            )
        source_files.append(source)
    if missing:
        return _materialization_metadata(
            "needs_inputs",
            elements,
            selection,
            None,
            reason_code="potcar_dataset_missing",
            message="One or more resolved POTCAR datasets are unavailable.",
            content_materialized=False,
            available_datasets=missing,
        )

    output.parent.mkdir(parents=True, exist_ok=True)
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            prefix=".POTCAR.",
            suffix=".tmp",
            dir=str(output.parent),
            delete=False,
        ) as temporary:
            temp_path = Path(temporary.name)
            os.chmod(temp_path, 0o600)
            for source in source_files:
                with source.open("rb") as handle:
                    shutil.copyfileobj(handle, temporary, length=1024 * 1024)
            temporary.flush()
            os.fsync(temporary.fileno())

        validation = validate_potcar(
            poscar_path,
            str(temp_path),
            expected_datasets=selection["resolved_datasets"],
        )
        if not validation["valid"]:
            temp_path.unlink(missing_ok=True)
            return _materialization_metadata(
                "error",
                elements,
                selection,
                validation,
                reason_code="materialized_potcar_validation_failed",
                message="Materialized POTCAR failed metadata validation.",
                content_materialized=False,
            )
        try:
            os.link(temp_path, output)
        except FileExistsError:
            temp_path.unlink(missing_ok=True)
            existing = validate_potcar(
                poscar_path,
                str(output),
                expected_datasets=selection["resolved_datasets"],
            )
            return _materialization_metadata(
                "existing" if existing["valid"] else "error",
                elements,
                selection,
                existing,
                reason_code=None if existing["valid"] else existing.get("reason_code"),
                message=existing["message"],
                content_materialized=False,
            )
        validation = validate_potcar(
            poscar_path,
            str(output),
            expected_datasets=selection["resolved_datasets"],
        )
        if not validation["valid"]:
            try:
                if output.samefile(temp_path):
                    output.unlink()
            except OSError:
                pass
            temp_path.unlink(missing_ok=True)
            return _materialization_metadata(
                "error",
                elements,
                selection,
                validation,
                reason_code="materialized_potcar_validation_failed",
                message="Materialized POTCAR failed final metadata validation.",
                content_materialized=False,
            )
        temp_path.unlink(missing_ok=True)
        result = _materialization_metadata(
            "materialized",
            elements,
            selection,
            validation,
            message="Restricted POTCAR materialized and validated.",
            content_materialized=True,
        )
        result["flavor"] = selected_flavor
        result["vaspkit_used"] = False
        result["vaspkit_requested"] = bool(use_vaspkit)
        return result
    except OSError:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)
        return _materialization_metadata(
            "error",
            elements,
            selection,
            None,
            reason_code="potcar_materialization_failed",
            message="Restricted POTCAR materialization failed.",
            content_materialized=False,
        )


def read_potcar_zval(potcar_path: str) -> List[float]:
    """Extract numerical ZVAL metadata from each POTCAR block."""
    zvals = []
    in_block = False
    with open(potcar_path, "r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            stripped = line.strip()
            if stripped.startswith("PAW"):
                in_block = True
                continue
            if in_block and "ZVAL" in stripped:
                for part in stripped.split(";"):
                    if "ZVAL" not in part:
                        continue
                    for token in part.split():
                        try:
                            zvals.append(float(token))
                            break
                        except ValueError:
                            continue
                    break
                in_block = False
    return zvals


def get_potcar_nelect(potcar_path: str, poscar_path: str) -> float:
    """Calculate total valence electrons from POTCAR ZVAL and POSCAR counts."""
    zvals = read_potcar_zval(potcar_path)
    species = read_poscar_species(poscar_path)
    if len(zvals) != len(species):
        raise ValueError(
            f"ZVAL count ({len(zvals)}) doesn't match POSCAR species count ({len(species)})"
        )
    with open(poscar_path, "r", encoding="utf-8") as handle:
        lines = [line.strip() for line in handle.readlines()]
    counts = [int(value) for value in lines[6].split()]
    return sum(zval * count for zval, count in zip(zvals, counts))
