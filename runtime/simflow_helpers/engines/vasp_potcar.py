"""POTCAR metadata helpers for VASP calculations.

SimFlow must never generate, concatenate, copy, move, print, snapshot, or
invoke external tools to produce POTCAR content. This module only supports
metadata-oriented inspection helpers such as POSCAR species order, POTCAR
header validation, and local library directory discovery.

Environment variables:
    SIMFLOW_VASP_POTCAR_PATH: Path to pseudopotential library root
        (e.g., /path/to/potpaw_PBE containing Si/, Ge/, O/ subdirs)
    SIMFLOW_VASP_POTCAR_FLAVOR: Functional type (PBE, LDA, PW91). Default: PBE
"""

import os
import re
from pathlib import Path
from typing import List, Optional


def get_potcar_path() -> Optional[str]:
    """Get pseudopotential library root from environment."""
    return os.environ.get("SIMFLOW_VASP_POTCAR_PATH")


def get_potcar_flavor() -> str:
    """Get POTCAR functional flavor from environment. Default: PBE."""
    return os.environ.get("SIMFLOW_VASP_POTCAR_FLAVOR", "PBE")


def read_poscar_species(poscar_path: str) -> List[str]:
    """Read POSCAR and return element species in order.

    Handles both VASP5 format (line 6 = species names) and VASP4 format
    (species names on line 6 or inferred from POTCAR).

    Args:
        poscar_path: Path to POSCAR file

    Returns:
        List of element symbols in POSCAR order, e.g., ['Si', 'Ge', 'O']

    Raises:
        FileNotFoundError: If POSCAR not found
        ValueError: If cannot parse species
    """
    with open(poscar_path, "r") as f:
        lines = [l.strip() for l in f.readlines()]

    if len(lines) < 6:
        raise ValueError(f"POSCAR too short ({len(lines)} lines)")

    # Line 0: comment
    # Line 1: scale factor
    # Lines 2-4: lattice vectors
    # Line 5: species names (VASP5) OR atom counts (VASP4)

    # Try VASP5 format first: line 5 has element names
    line5_parts = lines[5].split()
    # Check if line 5 looks like element names (not pure numbers)
    try:
        [int(x) for x in line5_parts]
        # Line 5 is numbers -> VASP4 format, no species info
        raise ValueError(
            "VASP4 POSCAR detected (no species line). "
            "Cannot determine element order. Add species names on line 6."
        )
    except ValueError as e:
        if "VASP4" in str(e):
            raise
        # Line 5 has non-numeric tokens -> VASP5 species line
        pass

    return line5_parts


def _find_element_potcar(potcar_root: str, flavor: str, element: str) -> Optional[Path]:
    """Find POTCAR file for a single element in the library.

    Searches for:
        $potcar_root/$flavor/$element/POTCAR
        $potcar_root/$flavor/${element}_*/POTCAR  (takes first match)

    Args:
        potcar_root: Library root directory
        flavor: Functional type (PBE, LDA, etc.)
        element: Element symbol (Si, Ge, etc.)

    Returns:
        Path to POTCAR file, or None if not found
    """
    flavor_dir = Path(potcar_root) / flavor
    if not flavor_dir.is_dir():
        return None

    # Exact match: $flavor/$element/POTCAR
    exact = flavor_dir / element / "POTCAR"
    if exact.is_file():
        return exact

    # Wildcard match: $flavor/${element}_*/POTCAR (e.g., Si_pv, Ge_h)
    # Prefer the base version (no suffix) over suffixed versions
    matches = sorted(flavor_dir.glob(f"{element}_*/POTCAR"))
    if matches:
        return matches[0]

    return None


def generate_potcar(
    poscar_path: str,
    output_path: str,
    potcar_root: str = None,
    flavor: str = None,
    use_vaspkit: bool = False,
) -> dict:
    """Compatibility API for deprecated POTCAR generation requests.

    Args:
        poscar_path: Path to POSCAR file
        output_path: Output POTCAR file path
        potcar_root: Compatibility-only pseudopotential library root
        flavor: Functional type (default: from env, fallback 'PBE')
        use_vaspkit: Compatibility-only VASPKIT toggle

    Returns:
        Metadata-only unavailable result. The requested output is never created
        or modified.
    """
    potcar_root_supplied = potcar_root is not None
    potcar_root = potcar_root or get_potcar_path()
    flavor = flavor or get_potcar_flavor()

    # Read elements from POSCAR
    try:
        elements = read_poscar_species(poscar_path)
    except (FileNotFoundError, ValueError) as e:
        return {"status": "error", "message": f"Cannot read POSCAR: {e}"}

    if not elements:
        return {"status": "error", "message": "No elements found in POSCAR"}

    return {
        "status": "unavailable",
        "reason_code": "potcar_generation_prohibited",
        "message": (
            "SimFlow does not generate, concatenate, copy, move, print, snapshot, "
            "or invoke VASPKIT to produce POTCAR content. The compatibility-only "
            "library-root and VASPKIT inputs are non-operative."
        ),
        "elements": elements,
        "potcar_path": None,
        "content_generated": False,
        "requested_output": str(output_path),
        "compatibility_inputs": {
            "potcar_root_supplied": potcar_root_supplied,
            "flavor": flavor,
            "use_vaspkit_supplied": bool(use_vaspkit),
        },
    }


def _list_available_elements(potcar_root: str, flavor: str) -> List[str]:
    """List available element directories in the pseudopotential library."""
    flavor_dir = Path(potcar_root) / flavor
    if not flavor_dir.is_dir():
        return []
    return sorted(
        d.name for d in flavor_dir.iterdir()
        if d.is_dir() and (d / "POTCAR").is_file()
    )


def validate_potcar(poscar_path: str, potcar_path: str) -> dict:
    """Validate that POTCAR element order matches POSCAR.

    Checks the first line of each element's POTCAR block (PAW header)
    against the POSCAR species order.

    Args:
        poscar_path: Path to POSCAR file
        potcar_path: Path to POTCAR file

    Returns:
        Dict with keys: valid, poscar_elements, potcar_elements, message
    """
    try:
        poscar_elements = read_poscar_species(poscar_path)
    except (FileNotFoundError, ValueError) as e:
        return {"valid": False, "message": f"Cannot read POSCAR: {e}"}

    if not Path(potcar_path).is_file():
        return {"valid": False, "message": "POTCAR not found"}

    # Extract element symbols from POTCAR PAW headers
    potcar_elements = _extract_potcar_elements(potcar_path)

    if poscar_elements == potcar_elements:
        return {
            "valid": True,
            "poscar_elements": poscar_elements,
            "potcar_elements": potcar_elements,
            "message": "Element order matches",
        }

    return {
        "valid": False,
        "poscar_elements": poscar_elements,
        "potcar_elements": potcar_elements,
        "message": (
            f"Element order mismatch. "
            f"POSCAR: {poscar_elements}, POTCAR: {potcar_elements}"
        ),
    }


def _extract_potcar_elements(potcar_path: str) -> List[str]:
    """Extract element symbols from POTCAR PAW headers.

    Each POTCAR block starts with a line like:
        PAW_PBE Si 05Jan2001  (PBE/PW91)
        PAW Si 05Jan2001       (LDA)
    """
    import re
    elements = []
    # PAW header: PAW[_<functional>] <Element> <date>
    # Element is 1-2 letters: uppercase + optional lowercase (Si, Ge, O, Fe, etc.)
    header_re = re.compile(r"^PAW(?:_\S+)?\s+([A-Z][a-z]?)\s+\d")
    with open(potcar_path, "r") as f:
        for line in f:
            m = header_re.match(line.strip())
            if m:
                elements.append(m.group(1))
    return elements


def read_potcar_zval(potcar_path: str) -> List[float]:
    """Extract ZVAL (valence electrons) from each POTCAR block.

    ZVAL appears in the line: POMASS = xx; ZVAL = yy

    Args:
        potcar_path: Path to POTCAR file

    Returns:
        List of ZVAL values, one per element, in POTCAR block order.
        e.g., [4.0] for Si, [4.0, 6.0] for Si+O
    """
    zvals = []
    in_block = False
    with open(potcar_path, "r") as f:
        for line in f:
            stripped = line.strip()
            if stripped.startswith("PAW"):
                in_block = True
                continue
            if in_block and "ZVAL" in stripped:
                # Format: POMASS = 28.085; ZVAL = 4.000
                for part in stripped.split(";"):
                    if "ZVAL" in part:
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
    """Calculate total valence electrons (NELECT) from POTCAR and POSCAR.

    NELECT = sum(ZVAL_i * count_i) where count_i is the number of atoms of each type.
    This is the VASP-internal NELECT, NOT the atomic-number total electrons.

    Args:
        potcar_path: Path to POTCAR file
        poscar_path: Path to POSCAR file

    Returns:
        Total valence electron count (float)

    Raises:
        ValueError: If ZVAL count doesn't match element count
    """
    zvals = read_potcar_zval(potcar_path)
    species = read_poscar_species(poscar_path)

    if len(zvals) != len(species):
        raise ValueError(
            f"ZVAL count ({len(zvals)}) doesn't match POSCAR species count ({len(species)})"
        )

    # Read atom counts from POSCAR (line 7 in VASP5 format)
    with open(poscar_path, "r") as f:
        lines = [l.strip() for l in f.readlines()]
    counts = [int(x) for x in lines[6].split()]

    nelect = 0.0
    for zval, count in zip(zvals, counts):
        nelect += zval * count

    return nelect
