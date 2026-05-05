#!/usr/bin/env python3
"""Create source-backed VASP troubleshooting summaries."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SIMFLOW_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(SIMFLOW_ROOT))

from runtime.lib.vasp_lookup import summarize_troubleshooting


def main() -> None:
    parser = argparse.ArgumentParser(description="Troubleshoot VASP issues using official docs")
    parser.add_argument("--issue", required=True, help="Parameter, error, or workflow issue")
    parser.add_argument("--context", default="{}", help="JSON context")
    parser.add_argument("--no-fetch", action="store_true", help="Do not fetch docs; return official URLs only")
    args = parser.parse_args()

    try:
        result = summarize_troubleshooting(
            issue=args.issue,
            context=json.loads(args.context),
            fetch=not args.no_fetch,
        )
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except Exception as exc:
        print(json.dumps({"status": "error", "message": str(exc)}, indent=2))
        sys.exit(1)


if __name__ == "__main__":
    main()
