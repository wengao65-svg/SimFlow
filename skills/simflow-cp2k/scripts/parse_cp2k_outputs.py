#!/usr/bin/env python3
"""Parse CP2K outputs from a user-specified calculation directory."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib.cp2k_parser import CP2KParser


def parse_cp2k_outputs(calc_dir: str, project: str | None = None, report: str | None = None) -> dict:
    result = CP2KParser().parse_outputs(str(Path(calc_dir).expanduser().resolve()), project=project)
    if report:
        path = Path(report).expanduser()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        result["report"] = str(path)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--calc-dir", required=True)
    parser.add_argument("--project", help="Preferred CP2K project prefix")
    parser.add_argument("--report", help="Optional JSON report path")
    args = parser.parse_args()
    try:
        result = parse_cp2k_outputs(args.calc_dir, args.project, args.report)
    except Exception as exc:
        print(json.dumps({"status": "error", "message": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
