#!/usr/bin/env python3
"""Run deterministic baseline QA checks for a rendered figure."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

_simflow_root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_simflow_root))

from runtime.simflow_core.script_contracts import add_helper_recording_args, maybe_record_helper_run


def _blank_report(figure_path: Path, output_path: Path | None) -> dict[str, Any]:
    return {
        "status": "pending",
        "figure": str(figure_path),
        "output": str(output_path) if output_path else None,
        "checks": {
            "exists": False,
            "non_empty": False,
            "readable": False,
            "dimensions": None,
            "near_blank": None,
            "alpha_channel": None,
        },
        "warnings": [],
        "metadata": {},
        "manual_review_required": [
            "clipped labels",
            "overlapping legends or ticks",
            "missing glyphs",
            "wrong units",
            "claim/caption consistency",
        ],
    }


def _write_report(report: dict[str, Any], output_path: Path | None) -> None:
    if output_path is None:
        return
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")


def audit_figure(figure: str, output: str | None = None) -> dict[str, Any]:
    """Audit a figure file for basic deterministic rendering problems."""
    figure_path = Path(figure).expanduser().resolve()
    output_path = Path(output).expanduser().resolve() if output else None
    report = _blank_report(figure_path, output_path)
    warnings = report["warnings"]
    checks = report["checks"]

    if not figure_path.exists():
        report["status"] = "error"
        warnings.append("Figure file does not exist.")
        _write_report(report, output_path)
        return report

    checks["exists"] = True
    stat = figure_path.stat()
    report["metadata"]["file_size_bytes"] = stat.st_size
    checks["non_empty"] = stat.st_size > 0
    if stat.st_size == 0:
        report["status"] = "error"
        warnings.append("Figure file is empty.")
        _write_report(report, output_path)
        return report

    if importlib.util.find_spec("PIL") is None:
        report["status"] = "skipped_optional_dependency"
        report["dependency"] = "Pillow"
        warnings.append("Pillow is not installed; only existence and file-size checks were completed.")
        _write_report(report, output_path)
        return report

    from PIL import Image, ImageStat

    try:
        with Image.open(figure_path) as image:
            image.load()
            checks["readable"] = True
            width, height = image.size
            checks["dimensions"] = {"width": width, "height": height}
            report["metadata"].update({
                "format": image.format,
                "mode": image.mode,
                "width": width,
                "height": height,
            })

            if width <= 1 or height <= 1:
                warnings.append("Figure dimensions are extremely small.")

            alpha_extrema = None
            if "A" in image.getbands():
                alpha = image.getchannel("A")
                alpha_extrema = alpha.getextrema()
                checks["alpha_channel"] = {
                    "present": True,
                    "min": alpha_extrema[0],
                    "max": alpha_extrema[1],
                }
                if alpha_extrema[1] == 0:
                    warnings.append("Figure appears fully transparent.")
                elif alpha_extrema[0] < 255:
                    warnings.append("Figure contains partial transparency; verify background rendering.")
            else:
                checks["alpha_channel"] = {"present": False}

            rgb = image.convert("RGB")
            extrema = rgb.getextrema()
            channel_ranges = [high - low for low, high in extrema]
            stat = ImageStat.Stat(rgb)
            checks["near_blank"] = max(channel_ranges) <= 3
            report["metadata"]["channel_extrema"] = [
                {"min": low, "max": high} for low, high in extrema
            ]
            report["metadata"]["channel_means"] = stat.mean
            if checks["near_blank"]:
                warnings.append("Figure pixels are nearly uniform; verify this is not a blank render.")

    except Exception as exc:
        report["status"] = "error"
        checks["readable"] = False
        warnings.append(f"Figure could not be read as an image: {exc}")
        _write_report(report, output_path)
        return report

    report["status"] = "warning" if warnings else "passed"
    _write_report(report, output_path)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit a rendered figure with deterministic baseline checks")
    parser.add_argument("--figure", required=True, help="Rendered figure path")
    parser.add_argument("--output", required=True, help="JSON audit report path")
    add_helper_recording_args(parser, default_stage="analysis_visualization")
    args = parser.parse_args()

    try:
        result = audit_figure(args.figure, args.output)
        result = maybe_record_helper_run(
            args=args,
            result=result,
            script_path=Path(__file__).resolve(),
            helper_name="audit_figure",
            input_paths=[args.figure],
            output_paths=[args.output],
            metadata={"helper_result_status": result.get("status"), "warnings": result.get("warnings", [])},
        )
        print(json.dumps(result, indent=2, ensure_ascii=False))
        if result.get("status") == "error":
            sys.exit(1)
    except Exception as exc:
        print(json.dumps({"status": "error", "message": str(exc)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
