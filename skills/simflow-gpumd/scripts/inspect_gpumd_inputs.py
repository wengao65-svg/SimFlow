#!/usr/bin/env python3
"""Inspect existing GPUMD/NEP inputs without executing or generating inputs."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

COMMON_GPUMD_FILES = ["run.in", "model.xyz"]
COMMON_NEP_FILES = ["nep.in", "train.xyz"]
REFERENCE_PATTERNS = [
    re.compile(r"\b(?:potential|model|dump|compute|velocity|force|basis|kpoints)\s+(?:file\s+)?([^\s#]+)", re.I),
    re.compile(r"\b(?:potential_file|model_file|basis_file|kpoints_file)\s*=?\s*([^\s#]+)", re.I),
]


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


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
        files.append({"path": str(path), "present": path.is_file()})
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
    return {
        "status": status,
        "software": software,
        "directory": str(directory),
        "mode": mode,
        "files": files,
        "referenced_files": referenced,
        "command_summary": command_summary,
        "warnings": warnings,
        "claim_limits": ["Static inspection cannot establish execution or scientific readiness."],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Statically inspect existing GPUMD/NEP inputs")
    parser.add_argument("--calculation-dir", default=".", help="Directory containing existing GPUMD/NEP files")
    parser.add_argument("--report", help="Optional JSON report path")
    args = parser.parse_args()

    result = inspect_directory(Path(args.calculation_dir))
    if args.report:
        report = Path(args.report).expanduser()
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        result["report"] = str(report)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
