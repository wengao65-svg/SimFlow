#!/usr/bin/env python3
"""Parse selected GPUMD/NEP table-like outputs conservatively."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from runtime.simflow_core.script_contracts import add_helper_recording_args, maybe_record_helper_run
from runtime.simflow_core.toolchains import support_level_for_capability


RECOGNIZED_ROLES = {
    "thermo.out": "thermo_table",
    "loss.out": "nep_loss_table",
    "msd.out": "msd_table",
    "rdf.out": "rdf_table",
    "hac.out": "heat_current_autocorrelation_table",
    "kappa.out": "thermal_conductivity_table",
    "dos.out": "density_of_states_table",
}


def _sha256(path: Path) -> str | None:
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


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
            "sha256": None,
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
    parser_status = "parsed" if parsed and not skipped else "partial" if parsed else "unparsed"
    ranges = []
    if column_count is not None:
        for index in range(column_count):
            values = [row[index] for row in rows]
            ranges.append({"column": index, "min": min(values), "max": max(values), "final": values[-1]})
    return {
        "path": str(path),
        "present": True,
        "bytes": path.stat().st_size if path.is_file() else None,
        "sha256": _sha256(path),
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


def main() -> None:
    parser = argparse.ArgumentParser(description="Parse selected GPUMD/NEP output tables")
    parser.add_argument("--files", nargs="+", required=True, help="Output files to parse")
    parser.add_argument("--software", choices=["auto", "gpumd", "nep"], default="auto")
    parser.add_argument("--output", default=None, help="Optional JSON summary output")
    add_helper_recording_args(parser, default_stage="analysis_visualization")
    args = parser.parse_args()

    parsed_files = [parse_table(Path(path).expanduser(), args.software) for path in args.files]
    blocked = all(item["parser_status"] in {"missing", "unparsed"} for item in parsed_files)
    degraded = any(item["parser_status"] != "parsed" or item.get("warnings") for item in parsed_files)
    result = {
        "status": "blocked" if blocked else ("warning" if degraded else "success"),
        "capability": "selected_output_parsing",
        "capability_support_level": support_level_for_capability(
            "nep" if all(item["software"] == "nep" for item in parsed_files) else "gpumd",
            "selected_output_parsing",
        ),
        "files": parsed_files,
        "limitations": [
            "Only simple numeric tables are parsed.",
            "No convergence, model-quality, or transport-property claim is made.",
        ],
    }
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        result["output_file"] = str(output)
    result = maybe_record_helper_run(
        args=args,
        result=result,
        script_path=Path(__file__).resolve(),
        helper_name="parse_gpumd_outputs",
        software="nep" if all(item["software"] == "nep" for item in parsed_files) else "gpumd",
        input_paths=args.files,
        output_paths=[args.output] if args.output else [],
        metadata={"capability": "selected_output_parsing", "helper_result_status": result.get("status")},
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
