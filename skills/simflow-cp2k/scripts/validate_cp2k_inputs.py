#!/usr/bin/env python3
"""Statically validate a CP2K calculation directory."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib.cp2k_validation import normalize_cp2k_task, validate_cp2k_inputs


def run_validation(task: str, calc_dir: str, input_path: str | None = None, report: str | None = None) -> dict:
    work_dir = Path(calc_dir).expanduser().resolve()
    deck = Path(input_path).expanduser() if input_path else None
    if deck is not None and not deck.is_absolute():
        deck = work_dir / deck
    result = validate_cp2k_inputs(normalize_cp2k_task(task), str(work_dir), input_path=str(deck) if deck else None)
    if report:
        path = Path(report).expanduser()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        result["report"] = str(path)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task", required=True)
    parser.add_argument("--calc-dir", required=True)
    parser.add_argument("--input-path", help="CP2K input deck relative to calc-dir or absolute")
    parser.add_argument("--report", help="Optional JSON report path")
    args = parser.parse_args()
    try:
        result = run_validation(args.task, args.calc_dir, args.input_path, args.report)
    except Exception as exc:
        print(json.dumps({"status": "error", "message": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
