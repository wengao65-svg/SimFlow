#!/usr/bin/env python3
"""Inspect existing GPUMD/NEP inputs without executing or generating inputs."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from runtime.simflow_core.helper_evidence import build_helper_evidence, source_file_record
from runtime.simflow_core.script_contracts import add_helper_recording_args, maybe_record_helper_run
from runtime.simflow_core.toolchains import helper_capabilities_for_tool, support_level_for_capability


COMMON_GPUMD_FILES = ["run.in", "model.xyz"]
COMMON_NEP_FILES = ["nep.in", "train.xyz"]
REFERENCE_PATTERNS = [
    re.compile(r"\b(?:potential|model|dump|compute|velocity|force|basis|kpoints)\s+(?:file\s+)?([^\s#]+)", re.I),
    re.compile(r"\b(?:potential_file|model_file|basis_file|kpoints_file)\s*=?\s*([^\s#]+)", re.I),
]


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _hash(path: Path) -> str | None:
    import hashlib

    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _commands(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    commands = []
    for line_no, raw in enumerate(_read(path).splitlines(), start=1):
        code = raw.split("#", 1)[0].strip()
        if not code:
            continue
        parts = code.split()
        commands.append({"line": line_no, "name": parts[0].lower(), "args": parts[1:], "text": code})
    return commands


def _references(path: Path) -> list[str]:
    if not path.is_file():
        return []
    refs: list[str] = []
    for line in _read(path).splitlines():
        code = line.split("#", 1)[0].strip()
        for pattern in REFERENCE_PATTERNS:
            refs.extend(match.group(1) for match in pattern.finditer(code))
    return [ref for ref in dict.fromkeys(refs) if not ref.startswith(("$", "{"))]


def inspect_directory(directory: Path) -> dict[str, Any]:
    directory = directory.resolve()
    run_in = directory / "run.in"
    nep_in = directory / "nep.in"
    mode = "mixed" if run_in.exists() and nep_in.exists() else "gpumd" if run_in.exists() else "nep" if nep_in.exists() else "unknown"
    expected = (COMMON_GPUMD_FILES if mode in {"gpumd", "mixed", "unknown"} else []) + (
        COMMON_NEP_FILES if mode in {"nep", "mixed", "unknown"} else []
    )
    files = []
    warnings = []
    for name in dict.fromkeys(expected):
        path = directory / name
        files.append({"path": str(path), "present": path.exists(), "sha256": _hash(path)})
        if not path.exists():
            warnings.append({"code": "missing_expected_file", "message": f"Expected file is absent: {name}"})

    input_paths = [path for path in [run_in, nep_in] if path.exists()]
    referenced = []
    for input_path in input_paths:
        for ref in _references(input_path):
            ref_path = (directory / ref).resolve()
            referenced.append({"source": str(input_path), "path": str(ref_path), "present": ref_path.exists()})
            if not ref_path.exists():
                warnings.append({"code": "missing_referenced_file", "message": f"{input_path.name} references missing file: {ref}"})

    command_summary = {}
    for input_path in input_paths:
        commands = _commands(input_path)
        names: dict[str, int] = {}
        for command in commands:
            names[command["name"]] = names.get(command["name"], 0) + 1
        command_summary[input_path.name] = {"command_count": len(commands), "commands": names}

    status = "blocked" if mode == "unknown" else ("warning" if warnings else "success")
    software = "gpumd" if mode != "nep" else "nep"
    return build_helper_evidence(
        helper="inspect_gpumd_inputs",
        capability="static_input_inspection",
        status=status,
        stage="computation",
        activity="static_input_inspection",
        evidence_role="gpumd_nep_input_inspection",
        source_files=[source_file_record(path) for path in input_paths],
        actual_tool_used={"software": software, "support_level": "tracked_only"},
        parser_status="not_applicable",
        claim_limits=[
            "Static input inspection does not validate GPUMD/NEP execution readiness.",
            "No input generation, execution, submit, or scientific readiness claim is made.",
        ],
        warnings=warnings,
        limitations=[
            "This is static inspection only.",
            "No GPUMD/NEP executable was called.",
            "No input generation or scientific readiness decision was performed.",
        ],
        capability_support_level=support_level_for_capability(software, "static_input_inspection"),
        tool_capabilities={
            "gpumd": helper_capabilities_for_tool("gpumd"),
            "nep": helper_capabilities_for_tool("nep"),
        },
        directory=str(directory),
        mode=mode,
        files=files,
        referenced_files=referenced,
        command_summary=command_summary,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Statically inspect existing GPUMD/NEP inputs")
    parser.add_argument("--calculation-dir", default=".", help="Directory containing existing GPUMD/NEP files")
    parser.add_argument("--output", default=None, help="Optional JSON output path")
    add_helper_recording_args(parser, default_stage="computation")
    args = parser.parse_args()

    result = inspect_directory(Path(args.calculation_dir))
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        result["output_file"] = str(output)
    result = maybe_record_helper_run(
        args=args,
        result=result,
        script_path=Path(__file__).resolve(),
        helper_name="inspect_gpumd_inputs",
        software="gpumd",
        input_paths=[str(Path(args.calculation_dir))],
        output_paths=[args.output] if args.output else [],
        metadata={"capability": "static_input_inspection", "helper_result_status": result.get("status")},
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
