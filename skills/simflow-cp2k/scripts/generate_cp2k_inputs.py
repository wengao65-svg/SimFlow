#!/usr/bin/env python3
"""Generate a CP2K input deck and coordinates in a user-specified directory."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib.cp2k_input import generate_cp2k_input_package


def generate_cp2k_inputs(
    structure_path: str,
    task: str,
    output_dir: str,
    params: dict | None = None,
    report: str | None = None,
    overwrite: bool = False,
) -> dict:
    result = generate_cp2k_input_package(structure_path, task, output_dir, params=params, overwrite=overwrite)
    if report:
        path = Path(report).expanduser()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        result["report"] = str(path)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--structure", required=True, help="CIF or XYZ structure file")
    parser.add_argument("--task", required=True, help="CP2K task")
    parser.add_argument("--output-dir", required=True, help="Calculation output directory")
    parser.add_argument("--params", default="{}", help="JSON parameter overrides")
    parser.add_argument("--report", help="Optional JSON report path")
    parser.add_argument("--overwrite", action="store_true", help="Explicitly replace existing CP2K inputs")
    args = parser.parse_args()
    try:
        result = generate_cp2k_inputs(args.structure, args.task, args.output_dir, json.loads(args.params), args.report, args.overwrite)
    except Exception as exc:
        print(json.dumps({"status": "error", "message": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
