#!/usr/bin/env python3
"""Summarize user-provided MLP metric files without readiness claims."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from runtime.simflow_core.helper_evidence import build_helper_evidence, source_file_record
from runtime.simflow_core.script_contracts import add_helper_recording_args, maybe_record_helper_run


def _load_metrics(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"path": str(path), "present": False, "metrics": {}, "warnings": [{"code": "missing_metrics_file", "message": "Metrics file is absent."}]}
    if path.suffix.lower() == ".json":
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            return {"path": str(path), "present": True, "format": "json", "metrics": {}, "warnings": [{"code": "invalid_metrics_json", "message": str(exc)}]}
        if isinstance(data, dict):
            metrics = {key: value for key, value in data.items() if isinstance(value, (int, float))}
            return {"path": str(path), "present": True, "format": "json", "metrics": metrics, "raw_keys": sorted(data)}
    metrics: dict[str, float] = {}
    with path.open("r", encoding="utf-8", errors="replace", newline="") as handle:
        sample = handle.read(2048)
        handle.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample) if "," in sample else csv.excel_tab
        except csv.Error:
            dialect = csv.excel_tab
        reader = csv.DictReader(handle, dialect=dialect)
        rows = list(reader)
    if rows:
        for key, value in rows[-1].items():
            try:
                metrics[key] = float(value)
            except (TypeError, ValueError):
                continue
    return {"path": str(path), "present": True, "format": "table", "rows": len(rows), "metrics": metrics}


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize MLP metric files")
    parser.add_argument("--metrics", nargs="+", required=True)
    parser.add_argument("--thresholds", default=None, help="Optional JSON object of metric thresholds")
    parser.add_argument("--output", default=None)
    add_helper_recording_args(parser, default_stage="analysis_visualization")
    args = parser.parse_args()

    threshold_data = json.loads(args.thresholds) if args.thresholds else {}
    summaries = [_load_metrics(Path(path).expanduser()) for path in args.metrics]
    comparisons = []
    for summary in summaries:
        for metric, value in summary.get("metrics", {}).items():
            if metric in threshold_data:
                comparisons.append({
                    "path": summary["path"],
                    "metric": metric,
                    "value": value,
                    "threshold": threshold_data[metric],
                    "within_threshold": value <= threshold_data[metric],
                })
    missing_or_empty = [summary for summary in summaries if not summary.get("present") or not summary.get("metrics")]
    result = build_helper_evidence(
        helper="summarize_mlp_metrics",
        capability="model_metrics_summary",
        status="blocked" if len(missing_or_empty) == len(summaries) else ("warning" if missing_or_empty else "success"),
        stage="analysis_visualization",
        activity="model_metrics_summary",
        evidence_role="model_metrics_summary",
        source_files=[source_file_record(path) for path in args.metrics],
        actual_tool_used={"software": "custom", "support_level": "tracked_only"},
        parser_status="missing" if len(missing_or_empty) == len(summaries) else ("partial" if missing_or_empty else "parsed"),
        claim_limits=[
            "Metric summaries do not certify production readiness.",
            "Metric units, splits, and validation domain must be reviewed from source context.",
        ],
        warnings=[
            warning
            for summary in summaries
            for warning in summary.get("warnings", [])
        ],
        limitations=[
            "Threshold comparisons are mechanical and do not certify production readiness.",
            "Metric units and split semantics must be reviewed from source context.",
        ],
        metric_files=summaries,
        threshold_comparisons=comparisons,
    )
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        result["output_file"] = str(output)
    result = maybe_record_helper_run(
        args=args,
        result=result,
        script_path=Path(__file__).resolve(),
        helper_name="summarize_mlp_metrics",
        software="custom",
        input_paths=args.metrics,
        output_paths=[args.output] if args.output else [],
        metadata={"evidence_role": "model_metrics_summary", "helper_result_status": result.get("status")},
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
