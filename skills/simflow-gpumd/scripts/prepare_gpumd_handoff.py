#!/usr/bin/env python3
"""Summarize user-selected GPUMD/NEP JSON reports for a human handoff."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


DEGRADED = {"warning", "blocked", "fail", "error", "incomplete"}


def summarize(paths: list[str], summary: str, next_actions: list[str]) -> dict:
    sources = []
    for value in paths:
        path = Path(value).expanduser()
        item = {"path": str(path), "present": path.is_file()}
        if path.is_file():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if not isinstance(data, dict):
                    raise ValueError("JSON root must be an object")
                item["source_status"] = data.get("status")
                item["parser_status"] = data.get("parser_status")
            except (json.JSONDecodeError, ValueError) as exc:
                item["parse_error"] = str(exc)
        sources.append(item)
    degraded = any(
        not item["present"] or item.get("parse_error")
        or str(item.get("source_status", "")).lower() in DEGRADED
        or str(item.get("parser_status", "")).lower() in {"partial", "missing", "malformed", "unrecognized"}
        for item in sources
    )
    return {
        "status": "blocked" if not sources else "warning" if degraded else "success",
        "summary": summary,
        "sources": sources,
        "next_actions": next_actions,
        "claim_limits": ["This handoff does not certify execution, convergence, or production readiness."],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", action="append", default=[])
    parser.add_argument("--inspection", action="append", default=[])
    parser.add_argument("--parsed-output", action="append", default=[])
    parser.add_argument("--summary", default="GPUMD/NEP report handoff")
    parser.add_argument("--next-action", action="append", default=[])
    parser.add_argument("--report", help="Optional JSON report path")
    args = parser.parse_args()
    result = summarize(args.manifest + args.inspection + args.parsed_output, args.summary, args.next_action)
    if args.report:
        report = Path(args.report).expanduser()
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        result["report"] = str(report)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
