"""Optional py4vasp adapter.

py4vasp is preferred when vaspout.h5 exists, but SimFlow keeps a parser
fallback for environments without py4vasp or VASP HDF5 output.
"""

from __future__ import annotations

import importlib
import importlib.util
from pathlib import Path
from typing import Any


def detect_py4vasp() -> dict[str, Any]:
    """Detect py4vasp without making it a hard dependency."""
    spec = importlib.util.find_spec("py4vasp")
    if spec is None:
        return {"available": False, "version": None, "message": "py4vasp not installed"}

    try:
        module = importlib.import_module("py4vasp")
        version = getattr(module, "__version__", None)
    except Exception as exc:  # pragma: no cover - defensive optional import
        return {"available": False, "version": None, "message": f"py4vasp import failed: {exc}"}

    return {"available": True, "version": version, "message": "py4vasp detected"}


def can_use_py4vasp(calc_dir: str) -> dict[str, Any]:
    """Return whether py4vasp should be the first analysis backend."""
    h5_path = Path(calc_dir) / "vaspout.h5"
    detection = detect_py4vasp()
    usable = detection["available"] and h5_path.is_file()
    return {
        "usable": usable,
        "calc_dir": str(Path(calc_dir)),
        "vaspout_h5": str(h5_path),
        "vaspout_h5_exists": h5_path.is_file(),
        "py4vasp": detection,
        "reason": "py4vasp and vaspout.h5 available" if usable else "missing py4vasp or vaspout.h5",
    }


def _safe_quantity_to_dict(quantity: Any) -> dict[str, Any]:
    """Extract compact py4vasp data without assuming one version's API."""
    for method in ("to_dict", "to_frame", "read"):
        attr = getattr(quantity, method, None)
        if not callable(attr):
            continue
        try:
            value = attr()
            if hasattr(value, "to_dict"):
                value = value.to_dict()
            return {"method": method, "data": value}
        except Exception as exc:
            last_error = str(exc)
    return {"method": None, "data": None, "error": locals().get("last_error", "no supported extractor")}


def read_with_py4vasp(calc_dir: str, quantity: str = "summary") -> dict[str, Any]:
    """Read a compact quantity from py4vasp, falling back at the caller."""
    usable = can_use_py4vasp(calc_dir)
    if not usable["usable"]:
        return {"status": "unavailable", **usable}

    try:
        py4vasp = importlib.import_module("py4vasp")
        calculation = py4vasp.Calculation.from_path(calc_dir)
        if quantity == "summary":
            names = ["energy", "structure", "force", "band", "dos"]
            available = [name for name in names if hasattr(calculation, name)]
            return {"status": "success", "backend": "py4vasp", "quantity": quantity, "available_quantities": available}

        if not hasattr(calculation, quantity):
            return {"status": "error", "backend": "py4vasp", "message": f"py4vasp quantity not available: {quantity}"}

        extracted = _safe_quantity_to_dict(getattr(calculation, quantity))
        return {"status": "success", "backend": "py4vasp", "quantity": quantity, **extracted}
    except Exception as exc:
        return {"status": "error", "backend": "py4vasp", "message": str(exc)}
