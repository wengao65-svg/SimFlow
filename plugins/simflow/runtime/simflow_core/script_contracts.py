"""Shared contract helpers for executable skill scripts."""

from __future__ import annotations

import shlex
import sys
from pathlib import Path
from typing import Any, Iterable

from .helpers import record_helper_run


def add_helper_recording_args(parser, *, default_stage: str) -> None:
    """Add standard optional helper-run recording CLI arguments."""
    existing = getattr(parser, "_option_string_actions", {})
    if "--project-root" not in existing:
        parser.add_argument(
            "--project-root",
            default=None,
            help="User project root for optional .simflow helper-run recording",
        )
    if "--stage" not in existing:
        parser.add_argument(
            "--stage",
            default=default_stage,
            help="Canonical SimFlow stage for optional helper-run recording",
        )
    if "--record-helper-run" not in existing:
        parser.add_argument(
            "--record-helper-run",
            action="store_true",
            help="Record this helper invocation as a SimFlow helper-run manifest",
        )


def require_project_root_for_recording(args) -> str | None:
    """Return project_root or raise when recording was requested without it."""
    if getattr(args, "record_helper_run", False) and not getattr(args, "project_root", None):
        raise ValueError("--project-root is required when --record-helper-run is set")
    return getattr(args, "project_root", None)


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (str, Path)):
        return [str(value)]
    if isinstance(value, Iterable):
        return [str(item) for item in value if item is not None]
    return [str(value)]


def _result_paths(result: dict[str, Any], keys: list[str]) -> list[str]:
    paths: list[str] = []
    for key in keys:
        paths.extend(_as_list(result.get(key)))
    return list(dict.fromkeys(paths))


def infer_input_paths(args, result: dict[str, Any]) -> list[str]:
    """Infer common input paths from argparse namespace and result dict."""
    paths: list[str] = []
    for key in ("input", "inputs", "input_file", "input_files", "file", "files", "structure", "trajectory"):
        paths.extend(_as_list(getattr(args, key, None)))
    paths.extend(_result_paths(result, ["input", "inputs", "input_file", "input_files"]))
    return list(dict.fromkeys(paths))


def infer_output_paths(args, result: dict[str, Any]) -> list[str]:
    """Infer common output paths from argparse namespace and result dict."""
    paths: list[str] = []
    for key in ("output", "outputs", "output_file", "output_files", "output_dir"):
        paths.extend(_as_list(getattr(args, key, None)))
    paths.extend(_result_paths(result, ["output", "outputs", "output_file", "output_files", "script_path"]))
    return list(dict.fromkeys(paths))


def maybe_record_helper_run(
    *,
    args,
    result: dict[str, Any],
    script_path: str | Path,
    helper_name: str,
    software: str | None = None,
    input_paths: list[str] | None = None,
    output_paths: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Record helper-run lineage when requested and return the original result.

    Helper scripts remain standalone by default. They only write `.simflow/`
    state when callers explicitly pass both `--record-helper-run` and
    `--project-root`.
    """
    if not getattr(args, "record_helper_run", False):
        return result

    project_root = require_project_root_for_recording(args)
    command = " ".join(shlex.quote(part) for part in sys.argv)
    recording = record_helper_run(
        project_root=project_root,
        stage=getattr(args, "stage", "analysis_visualization"),
        run_name=helper_name,
        command=command,
        script_path=str(script_path),
        input_paths=input_paths if input_paths is not None else infer_input_paths(args, result),
        output_paths=output_paths if output_paths is not None else infer_output_paths(args, result),
        environment={"python": sys.version.split()[0]},
        helper_name=helper_name,
        metadata=metadata or {"helper_result_status": result.get("status")},
        software=software,
    )
    result["helper_run_id"] = recording["run_id"]
    result["helper_run_manifest_artifact_id"] = recording["manifest_artifact"]["artifact_id"]
    return result
