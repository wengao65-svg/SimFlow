#!/usr/bin/env python3
"""Statically validate existing GPUMD/NEP inputs."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib.gpumd_inputs import validate_gpumd_inputs


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task", required=True)
    parser.add_argument("--calc-dir", required=True)
    parser.add_argument("--software", choices=["gpumd", "nep"], default="gpumd")
    parser.add_argument("--report", help="Optional JSON report path")
    args = parser.parse_args()
    try:
        result = validate_gpumd_inputs(args.task, args.calc_dir, software=args.software)
        if args.report:
            report = Path(args.report).expanduser()
            report.parent.mkdir(parents=True, exist_ok=True)
            report.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            result["report"] = str(report)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except Exception as exc:
        print(json.dumps({"status": "error", "message": str(exc)}, ensure_ascii=False))
        sys.exit(1)


if __name__ == "__main__":
    main()
