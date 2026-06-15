#!/usr/bin/env python3
"""Build an MLP dataset manifest from existing dataset files."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from runtime.simflow_core.helper_evidence import build_helper_evidence, source_file_record
from runtime.simflow_core.script_contracts import add_helper_recording_args, maybe_record_helper_run


def _sha256(path: Path) -> str | None:
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


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
        "sha256": _sha256(path),
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
    parser.add_argument("--parent-artifact", action="append", default=[])
    add_helper_recording_args(parser, default_stage="computation")
    args = parser.parse_args()

    splits = args.split + [None] * max(0, len(args.dataset) - len(args.split))
    records = [_dataset_record(path, splits[index]) for index, path in enumerate(args.dataset)]
    missing = [record for record in records if not record["present"]]
    degraded = missing + [record for record in records if record.get("warnings")]
    warnings = [
            {"code": "missing_dataset", "message": f"Dataset path does not exist: {record['path']}"}
            for record in missing
        ] + [
            warning
            for record in records
            for warning in record.get("warnings", [])
        ]
    manifest = build_helper_evidence(
        helper="build_mlp_dataset_manifest",
        capability="manifest_generation",
        status="blocked" if len(missing) == len(records) else ("warning" if degraded else "success"),
        stage="computation",
        activity="dataset_manifest_generation",
        evidence_role="dataset_manifest",
        source_files=[source_file_record(path) for path in args.dataset],
        actual_tool_used={"software": "custom", "support_level": "tracked_only"},
        parser_status="partial" if degraded and not missing else ("missing" if len(missing) == len(records) else "parsed"),
        claim_limits=[
            "Dataset manifests record provenance and counts only.",
            "Label convergence, model quality, and production readiness are not inferred.",
        ],
        warnings=warnings,
        limitations=[
            "Manifest records existing files only.",
            "Structure counts are best-effort for XYZ/EXTXYZ-like files.",
            "Label convergence and model readiness are not inferred.",
        ],
        parent_artifacts=args.parent_artifact,
        created_at=datetime.now(timezone.utc).isoformat(),
        recipe="mlp_md",
        iteration_id=args.iteration_id,
        toolchain=[item.strip() for item in args.toolchain.split(",")] if args.toolchain else [],
        label_source=args.label_source,
        datasets=records,
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    manifest["output_file"] = str(output)
    manifest = maybe_record_helper_run(
        args=args,
        result=manifest,
        script_path=Path(__file__).resolve(),
        helper_name="build_mlp_dataset_manifest",
        software="custom",
        input_paths=args.dataset,
        output_paths=[str(output)],
        metadata={"evidence_role": "dataset_manifest", "helper_result_status": manifest.get("status")},
    )
    print(json.dumps(manifest, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
