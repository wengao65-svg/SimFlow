#!/usr/bin/env python3
"""Parse selected GPUMD/NEP table-like outputs conservatively."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

RECOGNIZED_ROLES = {
    "thermo.out": "thermo_table",
    "loss.out": "nep_loss_table",
    "energy_train.out": "nep_energy_train_table",
    "energy_test.out": "nep_energy_test_table",
    "force_train.out": "nep_force_train_table",
    "force_test.out": "nep_force_test_table",
    "stress_train.out": "nep_stress_train_table",
    "stress_test.out": "nep_stress_test_table",
    "virial_train.out": "nep_virial_train_table",
    "virial_test.out": "nep_virial_test_table",
    "descriptor.out": "nep_descriptor_table",
    "msd.out": "msd_table",
    "rdf.out": "rdf_table",
    "hac.out": "heat_current_autocorrelation_table",
    "kappa.out": "thermal_conductivity_table",
    "dos.out": "density_of_states_table",
}


def _infer_software(path: Path, selected: str) -> str:
    if selected != "auto":
        return selected
    if path.name in {"loss.out", "energy_train.out", "energy_test.out", "force_train.out", "force_test.out", "stress_train.out", "stress_test.out", "virial_train.out", "virial_test.out", "descriptor.out"}:
        return "nep"
    return "gpumd"


def _numeric_row(line: str) -> list[float] | None:
    parts = line.split()
    if not parts:
        return None
    values = []
    for part in parts:
        try:
            value = float(part)
        except ValueError:
            return None
        if not math.isfinite(value):
            return None
        values.append(value)
    return values


def parse_table(path: Path, software: str) -> dict[str, Any]:
    inferred_software = _infer_software(path, software)
    if not path.exists():
        return {
            "path": str(path),
            "present": False,
            "bytes": None,
            "software": inferred_software,
            "parsed": False,
            "parser_status": "missing",
            "warnings": [{"code": "missing_output_file", "message": "File does not exist."}],
        }
    rows: list[list[float]] = []
    skipped = 0
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        row = _numeric_row(stripped)
        if row is None:
            skipped += 1
            continue
        rows.append(row)
    warnings = []
    widths = sorted({len(row) for row in rows})
    if not rows:
        warnings.append({"code": "no_numeric_rows", "message": "No numeric table rows were parsed."})
    if len(widths) > 1:
        warnings.append({"code": "inconsistent_column_count", "message": f"Parsed rows have inconsistent widths: {widths}"})
    column_count = widths[0] if len(widths) == 1 else None
    parsed = bool(rows) and column_count is not None
    if parsed and not skipped:
        parser_status = "parsed"
    elif parsed:
        parser_status = "partial"
    elif skipped:
        parser_status = "malformed"
    else:
        parser_status = "unrecognized"
    ranges = []
    if column_count is not None:
        for index in range(column_count):
            values = [row[index] for row in rows]
            ranges.append({"column": index, "min": min(values), "max": max(values), "final": values[-1]})
    return {
        "path": str(path),
        "present": True,
        "bytes": path.stat().st_size if path.is_file() else None,
        "software": inferred_software,
        "parsed": parsed,
        "parser_status": parser_status,
        "role": RECOGNIZED_ROLES.get(path.name, "unknown_table"),
        "rows": len(rows),
        "columns": column_count,
        "skipped_non_numeric_lines": skipped,
        "final_row": rows[-1] if rows else None,
        "column_ranges": ranges,
        "warnings": warnings,
    }


def _overall_parser_status(parsed_files: list[dict[str, Any]]) -> str:
    statuses = [item["parser_status"] for item in parsed_files]
    if all(status == "missing" for status in statuses):
        return "missing"
    if any(status in {"parsed", "partial"} for status in statuses):
        return "partial" if any(status != "parsed" for status in statuses) else "parsed"
    if any(status == "malformed" for status in statuses):
        return "malformed"
    return "unrecognized"


def main() -> None:
    parser = argparse.ArgumentParser(description="Parse selected GPUMD/NEP output tables")
    parser.add_argument("--files", nargs="+", required=True, help="Output files to parse")
    parser.add_argument("--software", choices=["auto", "gpumd", "nep"], default="auto")
    parser.add_argument("--report", help="Optional JSON summary path")
    args = parser.parse_args()

    parsed_files = [parse_table(Path(path).expanduser(), args.software) for path in args.files]
    overall_parser_status = _overall_parser_status(parsed_files)
    blocked = all(item["parser_status"] in {"missing", "unrecognized", "malformed"} for item in parsed_files)
    degraded = any(item["parser_status"] != "parsed" or item.get("warnings") for item in parsed_files)
    software = "nep" if all(item["software"] == "nep" for item in parsed_files) else "gpumd"
    result = {
        "status": "blocked" if blocked else ("warning" if degraded else "success"),
        "software": software,
        "parser_status": overall_parser_status,
        "files": parsed_files,
        "claim_limits": [
            "Numeric parsing does not establish convergence, model quality, or transport properties.",
            "Review column meaning and units against the original GPUMD/NEP context.",
        ],
    }
    if args.report:
        report = Path(args.report).expanduser()
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        result["report"] = str(report)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
