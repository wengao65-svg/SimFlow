#!/usr/bin/env python3
"""Generate GPUMD/NEP inputs in an explicitly chosen calculation directory."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib.gpumd_inputs import generate_gpumd_inputs as generate_inputs


def generate_gpumd_inputs(
    structure_path: str | None,
    task: str,
    output_dir: str,
    params: dict | None = None,
    software: str = "gpumd",
    overwrite: bool = False,
) -> dict:
    return generate_inputs(
        structure_path, task, output_dir,
        params=params, software=software, overwrite=overwrite,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--structure", help="Structure file for model.xyz")
    parser.add_argument("--task", required=True)
    parser.add_argument("--output-dir", required=True, help="Calculation directory")
    parser.add_argument("--software", choices=["gpumd", "nep"], default="gpumd")
    parser.add_argument("--params", default="{}", help="JSON parameter overrides")
    parser.add_argument("--overwrite", action="store_true", help="Explicitly replace existing inputs")
    args = parser.parse_args()
    try:
        result = generate_gpumd_inputs(
            args.structure, args.task, args.output_dir,
            params=json.loads(args.params), software=args.software,
            overwrite=args.overwrite,
        )
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except Exception as exc:
        print(json.dumps({"status": "error", "message": str(exc)}, ensure_ascii=False))
        sys.exit(1)


if __name__ == "__main__":
    main()
