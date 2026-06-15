#!/usr/bin/env python3
"""Build a provenance manifest for existing GPUMD/NEP evidence files."""

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
from runtime.simflow_core.toolchains import build_actual_tool_used, classify_tool_support, support_level_for_capability
from runtime.simflow_helpers.adapters import adapter_capabilities


def _sha256(path: Path) -> str | None:
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _file_record(path: str) -> dict[str, Any]:
    candidate = Path(path).expanduser()
    return {
        "path": str(candidate),
        "present": candidate.exists(),
        "is_file": candidate.is_file(),
        "bytes": candidate.stat().st_size if candidate.is_file() else None,
        "sha256": _sha256(candidate),
    }


def _parse_environment(value: str | None) -> tuple[Any, list[dict[str, str]]]:
    if not value:
        return None, []
    try:
        return json.loads(value), []
    except json.JSONDecodeError as exc:
        return None, [{
            "code": "invalid_environment_json",
            "message": f"--environment is not valid JSON and was recorded as unavailable: {exc.msg}",
        }]


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    toolchain = [tool.strip() for tool in args.toolchain.split(",") if tool.strip()] or [args.software]
    support = classify_tool_support(toolchain)
    environment, warnings = _parse_environment(args.environment)
    actual_tool_used = build_actual_tool_used(
        {"software": args.software, "helper_support": support},
        args.software,
        command=args.command,
        version=args.version,
        environment=environment,
    )
    manifest = build_helper_evidence(
        helper="build_gpumd_manifest",
        capability="manifest_generation",
        status="success",
        stage="computation",
        activity="manifest_generation",
        evidence_role=args.evidence_role,
        source_files=[source_file_record(path) for path in args.files],
        actual_tool_used=actual_tool_used,
        parser_status="not_applicable",
        claim_limits=[
            "No GPUMD/NEP executable was called.",
            "No input generation, execution, submit, or scientific readiness claim is made.",
        ],
        warnings=warnings,
        limitations=[
            "Manifest generation records user-provided evidence only.",
            "No GPUMD/NEP executable was called.",
            "Input generation and submit are not helper-supported capabilities.",
        ],
        parent_artifacts=args.parent_artifact,
        created_at=datetime.now(timezone.utc).isoformat(),
        recipe=args.recipe,
        iteration_id=args.iteration_id,
        capability_support_level=support_level_for_capability(args.software, "manifest_generation"),
        adapter_capabilities=adapter_capabilities(args.software),
        toolchain=toolchain,
        tool_support=support,
        files=[_file_record(path) for path in args.files],
    )
    missing = [item for item in manifest["files"] if not item["present"]]
    warnings.extend([
        {"code": "missing_manifest_file", "message": f"Manifest path does not exist: {item['path']}"}
        for item in missing
    ])
    manifest["warnings"] = warnings
    if missing and len(missing) == len(manifest["files"]):
        manifest["status"] = "blocked"
    elif warnings:
        manifest["status"] = "warning"
    manifest["warnings"] = warnings
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a GPUMD/NEP evidence manifest")
    parser.add_argument("--files", nargs="+", required=True, help="Existing evidence files to include")
    parser.add_argument("--output", required=True, help="JSON manifest output path")
    parser.add_argument("--software", default="gpumd", choices=["gpumd", "nep"])
    parser.add_argument("--toolchain", default="gpumd,nep")
    parser.add_argument("--command", default=None, help="User-provided command string; not executed")
    parser.add_argument("--version", default=None)
    parser.add_argument("--environment", default=None, help="JSON environment note")
    parser.add_argument("--recipe", default="mlp_md")
    parser.add_argument("--iteration-id", default=None)
    parser.add_argument("--evidence-role", default="gpumd_nep_manifest")
    parser.add_argument("--parent-artifact", action="append", default=[])
    add_helper_recording_args(parser, default_stage="computation")
    args = parser.parse_args()

    manifest = build_manifest(args)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    manifest["output_file"] = str(output)
    manifest = maybe_record_helper_run(
        args=args,
        result=manifest,
        script_path=Path(__file__).resolve(),
        helper_name="build_gpumd_manifest",
        software=args.software,
        input_paths=args.files,
        output_paths=[str(output)],
        metadata={"capability": "manifest_generation", "helper_result_status": manifest.get("status")},
    )
    print(json.dumps(manifest, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
