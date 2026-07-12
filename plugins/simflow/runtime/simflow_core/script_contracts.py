"""Shared contract helpers for executable skill scripts."""

from __future__ import annotations

import json
import re
import shlex
import sys
from pathlib import Path
from typing import Any, Iterable

from .helper_evidence import helper_evidence_summary
from .helpers import record_helper_run
from .result_contract import attach_simflow_result, extract_helper_evidence_payload


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
    if "--parent-artifact" not in existing:
        parser.add_argument(
            "--parent-artifact",
            action="append",
            default=None,
            help="Parent artifact ID to attach to helper outputs and manifests; repeatable",
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


def _helper_evidence_summary(payload: dict[str, Any], *, stage: str | None, helper_name: str) -> dict[str, Any]:
    return helper_evidence_summary(
        {
            "stage": stage,
            "metadata": {
                "helper_evidence": payload,
                "helper_name": helper_name,
                "helper_result_status": payload.get("status"),
            },
            "lineage": {"parameters": {}},
        }
    )


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


_GENERIC_SENSITIVE_KEY_RE = re.compile(
    r"(password|passwd|pwd|token|secret|api[_-]?key|credential|credentials)",
    re.IGNORECASE,
)
_DEFAULT_SENSITIVE_JSON_KEYS = {
    "potcar_root",
    "potcar_path",
    "potcar_dir",
    "potcar_library",
    "potcar_lib",
    "simflow_vasp_potcar_path",
    "vasp_potcar_path",
    "vasp_potcar_root",
    "potpaw",
    "potpaw_pbe",
    "potpaw_lda",
    "potpaw_gga",
}


def _normalize_sensitive_key(key: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(key).strip().lower()).strip("_")


def _is_sensitive_json_key(key: str, explicit_keys: Iterable[str] | None = None) -> bool:
    normalized = _normalize_sensitive_key(key)
    explicit = {
        _normalize_sensitive_key(item)
        for item in (explicit_keys or [])
    }
    if normalized in _DEFAULT_SENSITIVE_JSON_KEYS or normalized in explicit:
        return True
    if _GENERIC_SENSITIVE_KEY_RE.search(str(key)):
        return True
    if "potcar" in normalized and any(part in normalized for part in ("path", "root", "dir", "library", "lib")):
        return True
    if normalized.startswith("simflow_vasp_potcar"):
        return True
    return False


def _sanitize_json_value(value: Any, explicit_keys: Iterable[str] | None = None) -> Any:
    if isinstance(value, dict):
        sanitized = {}
        for key, child in value.items():
            if _is_sensitive_json_key(str(key), explicit_keys):
                sanitized[key] = "<redacted>"
            else:
                sanitized[key] = _sanitize_json_value(child, explicit_keys)
        return sanitized
    if isinstance(value, list):
        return [_sanitize_json_value(item, explicit_keys) for item in value]
    return value


def _redact_json_cli_value(value: str, explicit_keys: Iterable[str] | None = None) -> str:
    try:
        decoded = json.loads(value)
    except json.JSONDecodeError:
        return "<redacted>"
    sanitized = _sanitize_json_value(decoded, explicit_keys)
    return json.dumps(sanitized, ensure_ascii=False, sort_keys=True)


def _redact_cli_args(
    argv: list[str],
    sensitive_options: Iterable[str] | None,
    sensitive_json_options: dict[str, Iterable[str]] | None = None,
) -> list[str]:
    options = {str(option) for option in sensitive_options or []}
    json_options = {str(option): keys for option, keys in (sensitive_json_options or {}).items()}
    if not options and not json_options:
        return list(argv)

    redacted: list[str] = []
    index = 0
    while index < len(argv):
        token = argv[index]
        if token in json_options:
            redacted.append(token)
            if index + 1 < len(argv):
                redacted.append(_redact_json_cli_value(argv[index + 1], json_options[token]))
                index += 2
                continue
            index += 1
            continue
        if token in options:
            redacted.append(token)
            if index + 1 < len(argv):
                redacted.append("<redacted>")
                index += 2
                continue
            index += 1
            continue
        else:
            json_matched = next((option for option in json_options if token.startswith(f"{option}=")), None)
            if json_matched is not None:
                raw_value = token[len(json_matched) + 1:]
                redacted.append(f"{json_matched}={_redact_json_cli_value(raw_value, json_options[json_matched])}")
                index += 1
                continue
            matched = next((option for option in options if token.startswith(f"{option}=")), None)
            if matched is not None:
                redacted.append(f"{matched}=<redacted>")
                index += 1
                continue
        redacted.append(token)
        index += 1
    return redacted


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
    sensitive_cli_options: Iterable[str] | None = None,
    sensitive_json_cli_options: dict[str, Iterable[str]] | None = None,
) -> dict[str, Any]:
    """Record helper-run lineage when requested and return the original result.

    Helper scripts remain standalone by default. They only write `.simflow/`
    state when callers explicitly pass both `--record-helper-run` and
    `--project-root`.
    """
    if not getattr(args, "record_helper_run", False):
        return result

    project_root = require_project_root_for_recording(args)
    simflow_result = result.get("simflow_result")
    if isinstance(simflow_result, dict):
        if simflow_result.get("role") == "helper":
            result["simflow_result"] = {
                **simflow_result,
                "state_effect": "record_only",
            }
    else:
        attach_simflow_result(
            result,
            role="helper",
            activity=helper_name,
            legacy_status=result.get("status"),
            stage=getattr(args, "stage", "analysis_visualization"),
            state_effect="record_only",
        )
    helper_evidence = extract_helper_evidence_payload(result)
    recording_metadata = dict(metadata or {})
    recording_metadata.setdefault("helper_result_status", result.get("status"))
    recording_metadata["simflow_result"] = result["simflow_result"]
    if helper_evidence:
        recording_metadata["helper_evidence"] = helper_evidence
        recording_metadata["helper_evidence_summary"] = _helper_evidence_summary(
            helper_evidence,
            stage=getattr(args, "stage", "analysis_visualization"),
            helper_name=helper_name,
        )
    command = " ".join(
        shlex.quote(part)
        for part in _redact_cli_args(sys.argv, sensitive_cli_options, sensitive_json_cli_options)
    )
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
        parent_artifacts=_as_list(getattr(args, "parent_artifact", None)),
        metadata=recording_metadata,
        software=software,
    )
    result["helper_run_id"] = recording["run_id"]
    result["helper_run_manifest_artifact_id"] = recording["manifest_artifact"]["artifact_id"]
    return result
