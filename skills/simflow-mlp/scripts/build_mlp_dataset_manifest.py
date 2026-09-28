#!/usr/bin/env python3
"""Build an MLP dataset manifest from existing dataset files."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
from metadata import source_file_record


def _count_extxyz_frames(path: Path) -> int | None:
    if not path.is_file():
        return None
    frames = 0
    try:
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            while True:
                first = handle.readline()
                if first == "":
                    return frames
                if not first.strip():
                    return None
                try:
                    atoms = int(first.strip())
                except ValueError:
                    return None
                comment = handle.readline()
                if comment == "":
                    return None
                for _ in range(atoms):
                    if handle.readline() == "":
                        return None
                frames += 1
    except OSError:
        return None


def _dataset_record(path_value: str, split: str | None) -> dict[str, Any]:
    path = Path(path_value).expanduser()
    record = {
        "path": str(path),
        "split": split,
        "present": path.exists(),
        "bytes": path.stat().st_size if path.is_file() else None,
        "format_hint": path.suffix.lstrip(".") or None,
        "structure_count": None,
    }
    if path.suffix.lower() in {".xyz", ".extxyz"}:
        record["structure_count"] = _count_extxyz_frames(path)
        if record["present"] and record["structure_count"] is None:
            record["warnings"] = [{"code": "structure_count_unavailable", "message": "Could not count XYZ/EXTXYZ frames with the streaming parser."}]
    return record


def main() -> None:
    parser = argparse.ArgumentParser(description="Build an MLP dataset manifest")
    parser.add_argument("--dataset", action="append", required=True, help="Dataset path; repeat for multiple files")
    parser.add_argument("--split", action="append", default=[], help="Optional split labels matching --dataset order")
    parser.add_argument("--output", required=True, help="Manifest JSON output")
    parser.add_argument("--toolchain", default=None, help="Comma-separated toolchain")
    parser.add_argument("--label-source", default=None)
    parser.add_argument("--iteration-id", default=None)
    args = parser.parse_args()

    splits = args.split + [None] * max(0, len(args.dataset) - len(args.split))
    records = [_dataset_record(path, splits[index]) for index, path in enumerate(args.dataset)]
    missing = [record for record in records if not record["present"]]
    missing_splits = [record for record in records if not record.get("split")]
    label_source_missing = not bool(args.label_source)
    lineage_complete = bool(records) and not missing and not missing_splits and bool(args.label_source)
    degraded = missing + missing_splits + [record for record in records if record.get("warnings")]
    if label_source_missing:
        degraded.append({"label_source": None})
    warnings = [
        {"code": "missing_dataset", "message": f"Dataset path does not exist: {record['path']}"}
        for record in missing
    ] + [
        {"code": "missing_split", "message": f"Dataset split is not recorded for: {record['path']}"}
        for record in missing_splits
    ] + (
        [{"code": "missing_label_source", "message": "Reference label source is not recorded."}]
        if label_source_missing
        else []
    ) + [
        warning
        for record in records
        for warning in record.get("warnings", [])
    ]
    manifest = {
        "helper": "build_mlp_dataset_manifest",
        "capability": "manifest_generation",
        "evidence_role": "dataset_manifest",
        "status": "blocked" if len(missing) == len(records) else ("warning" if degraded else "success"),
        "source_files": [source_file_record(path) for path in args.dataset],
        "parser_status": "missing" if len(missing) == len(records) else ("partial" if degraded else "parsed"),
        "claim_limits": [
            "Dataset manifests record provenance and counts only.",
            "Label convergence, model quality, and production readiness are not inferred.",
        ],
        "warnings": warnings,
        "limitations": [
            "Manifest records existing files only.",
            "Structure counts are best-effort for XYZ/EXTXYZ-like files.",
            "Label convergence and model readiness are not inferred.",
        ],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "recipe": "mlp_md",
        "iteration_id": args.iteration_id,
        "toolchain": [item.strip() for item in args.toolchain.split(",")] if args.toolchain else [],
        "label_source": args.label_source,
        "label_provenance_recorded": bool(args.label_source),
        "split_complete": not missing_splits,
        "lineage_complete": lineage_complete,
        "datasets": records,
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    manifest["output_file"] = str(output)
    print(json.dumps(manifest, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
