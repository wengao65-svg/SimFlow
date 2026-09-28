#!/usr/bin/env python3
"""List user-selected GPUMD/NEP evidence files without copying their contents."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def build_manifest(paths: list[str], software: str) -> dict:
    files = []
    for value in paths:
        path = Path(value).expanduser()
        files.append({
            "path": str(path),
            "present": path.is_file(),
            "bytes": path.stat().st_size if path.is_file() else None,
        })
    missing = [item["path"] for item in files if not item["present"]]
    return {
        "status": "blocked" if len(missing) == len(files) else "warning" if missing else "success",
        "software": software,
        "files": files,
        "missing_files": missing,
        "claim_limits": ["File presence does not establish execution, convergence, or model quality."],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--files", nargs="+", required=True)
    parser.add_argument("--software", choices=["gpumd", "nep"], default="gpumd")
    parser.add_argument("--report", help="Optional JSON report path")
    args = parser.parse_args()
    result = build_manifest(args.files, args.software)
    if args.report:
        report = Path(args.report).expanduser()
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        result["report"] = str(report)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
