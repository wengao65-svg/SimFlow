#!/usr/bin/env python3
"""Audit SimFlow skill helper scripts for workflow-layer contracts."""

from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SKILL_SCRIPT_GLOB = "skills/*/scripts/*.py"


STAGE_RUNNER_FUNCTIONS = {
    "run_modeling_stage",
    "run_input_generation_stage",
    "run_compute_stage",
    "run_analysis_stage",
    "run_visualization_stage",
    "run_writing_stage",
    "verify_workflow",
}


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _functions(tree: ast.AST) -> dict[str, ast.FunctionDef]:
    return {node.name: node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}


def _function_args(node: ast.FunctionDef) -> list[str]:
    return [arg.arg for arg in node.args.args]


def _has_argparse_option(tree: ast.AST, option: str) -> bool:
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Attribute) or node.func.attr != "add_argument":
            continue
        for arg in node.args:
            if isinstance(arg, ast.Constant) and arg.value == option:
                return True
    return False


def _uses_standard_recording_args(tree: ast.AST) -> bool:
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name) and func.id == "add_helper_recording_args":
            return True
        if isinstance(func, ast.Attribute) and func.attr == "add_helper_recording_args":
            return True
    return False


def _category(path: Path, functions: dict[str, ast.FunctionDef]) -> str:
    names = set(functions)
    if names & STAGE_RUNNER_FUNCTIONS:
        return "stage_runner"
    if path.name.startswith("_"):
        return "shared_module"
    return "helper_cli"


def audit_script(path: Path) -> dict[str, Any]:
    relative = str(path.relative_to(ROOT))
    text = _read(path)
    tree = ast.parse(text)
    functions = _functions(tree)
    category = _category(path, functions)
    stage_runner_names = sorted(set(functions) & STAGE_RUNNER_FUNCTIONS)
    uses_standard_recording_args = _uses_standard_recording_args(tree)
    stage_runner_contract = None
    if stage_runner_names:
        runner = functions[stage_runner_names[0]]
        stage_runner_contract = _function_args(runner)[:3] == ["workflow_dir", "params", "dry_run"]

    report = {
        "path": relative,
        "category": category,
        "has_main": "main" in functions,
        "stage_runner_functions": stage_runner_names,
        "stage_runner_contract": stage_runner_contract,
        "has_project_root_option": uses_standard_recording_args or _has_argparse_option(tree, "--project-root"),
        "has_stage_option": uses_standard_recording_args or _has_argparse_option(tree, "--stage"),
        "has_record_helper_run_option": uses_standard_recording_args or _has_argparse_option(tree, "--record-helper-run"),
        "uses_standard_recording_args": uses_standard_recording_args,
        "uses_record_helper_run": "record_helper_run" in text,
        "mentions_omx": ".omx" in text,
        "writes_simflow_literal": ".simflow" in text,
    }
    return report


def audit_skill_scripts(root: Path = ROOT) -> list[dict[str, Any]]:
    scripts = sorted(root.glob(SKILL_SCRIPT_GLOB))
    return [audit_script(path) for path in scripts]


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit SimFlow skill helper script contracts")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    args = parser.parse_args()

    reports = audit_skill_scripts()
    if args.json:
        print(json.dumps(reports, indent=2, ensure_ascii=False))
        return

    for report in reports:
        flags = []
        if report["category"] == "stage_runner" and not report["stage_runner_contract"]:
            flags.append("bad-stage-runner-signature")
        if report["category"] == "helper_cli":
            for key, label in [
                ("has_project_root_option", "missing-project-root"),
                ("has_stage_option", "missing-stage"),
                ("has_record_helper_run_option", "missing-record-helper-run"),
            ]:
                if not report[key]:
                    flags.append(label)
        if report["mentions_omx"]:
            flags.append("mentions-.omx")
        status = "OK" if not flags else "WARN"
        print(f"{status}\t{report['category']}\t{report['path']}\t{','.join(flags)}")


if __name__ == "__main__":
    main()
