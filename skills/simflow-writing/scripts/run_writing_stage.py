#!/usr/bin/env python3
"""Run the canonical writing stage for Milestone D."""

from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from runtime.simflow_core.artifacts import list_artifacts, register_artifact
from runtime.simflow_core.proposals import load_proposal_contract
from runtime.simflow_core.state import read_state


def _load_function(relative_script: str, function_name: str, module_name: str):
    script_path = ROOT / relative_script
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return getattr(module, function_name)


BUILD_REPRODUCIBILITY_PACKAGE = _load_function(
    "skills/simflow-writing/scripts/build_reproducibility_package.py",
    "build_reproducibility_package",
    "simflow_build_reproducibility_package",
)
GENERATE_FINAL_HANDOFF = _load_function(
    "skills/simflow-handoff/scripts/generate_final_handoff.py",
    "generate_final_handoff",
    "simflow_generate_final_handoff",
)
VERIFY_WORKFLOW = _load_function(
    "skills/simflow-verify/scripts/verify_workflow.py",
    "verify_workflow",
    "simflow_verify_workflow",
)


REQUIRED_ARTIFACTS = {
    "proposal": "proposal.md",
    "parameter_table": "parameter_table.csv",
    "research_questions": "research_questions.json",
    "structure_manifest": "structure_manifest.json",
    "compute_plan": "compute_plan.json",
    "analysis_report": "analysis_report.json",
    "figures_manifest": "figures_manifest.json",
}
CANONICAL_STAGE_SEQUENCE = [
    "literature_review",
    "proposal",
    "modeling",
    "computation",
    "analysis_visualization",
    "writing",
]


def resolve_project_root_from_workflow_dir(workflow_dir: str) -> Path:
    path = Path(workflow_dir).expanduser().resolve()
    return path.parent if path.name == ".simflow" else path


def _relative_path(project_root: Path, path: Path) -> str:
    return str(path.resolve().relative_to(project_root))


def _latest_artifact(project_root: Path, artifact_name: str) -> dict[str, Any] | None:
    matches = [
        artifact
        for artifact in list_artifacts(project_root=str(project_root))
        if artifact.get("name") == artifact_name
    ]
    return matches[-1] if matches else None


def _resolve_required_artifacts(project_root: Path) -> dict[str, dict[str, Any]]:
    resolved: dict[str, dict[str, Any]] = {}
    missing: list[str] = []
    for key, artifact_name in REQUIRED_ARTIFACTS.items():
        artifact = _latest_artifact(project_root, artifact_name)
        if artifact is None:
            missing.append(artifact_name)
            continue
        artifact_path = project_root / artifact["path"]
        if not artifact_path.is_file():
            missing.append(artifact_name)
            continue
        resolved[key] = artifact
    if missing:
        raise FileNotFoundError(f"Missing writing inputs: {', '.join(sorted(set(missing)))}")
    return resolved


def _stage_index(stage: str | None) -> int:
    if stage in CANONICAL_STAGE_SEQUENCE:
        return CANONICAL_STAGE_SEQUENCE.index(stage)
    return 0


def _allows_partial_writing_entry(metadata: dict[str, Any], state: dict[str, Any]) -> bool:
    entry_stage = metadata.get("entry_point") or state.get("entry_point")
    current_stage = metadata.get("current_stage") or state.get("current_stage")
    return max(_stage_index(entry_stage), _stage_index(current_stage)) >= _stage_index("writing")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_parameter_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _modeling_summary(structure_manifest: dict[str, Any]) -> list[str]:
    lines = []
    source_mode = structure_manifest.get("source_mode", "unknown")
    structure_files = structure_manifest.get("structure_files", [])
    validation = structure_manifest.get("validation", {})
    lines.append(f"- Source mode: {source_mode}")
    lines.append(f"- Structure files: {', '.join(structure_files) if structure_files else 'none'}")
    lines.append(f"- Validation status: {validation.get('status', 'unknown')}")
    return lines


def _compute_summary(compute_plan: dict[str, Any]) -> list[str]:
    resources = compute_plan.get("resource_estimate", {})
    lines = [
        f"- Task: {compute_plan.get('task', 'unknown')}",
        f"- Scheduler: {compute_plan.get('scheduler', 'unknown')}",
        f"- Recommended command: {compute_plan.get('recommended_command', 'unknown')}",
        f"- Dry-run: {compute_plan.get('dry_run', True)}",
        f"- Real submit: {compute_plan.get('real_submit', False)}",
    ]
    if resources:
        lines.append(
            "- Resource estimate: "
            f"nodes={resources.get('recommended_nodes', 'n/a')}, "
            f"ntasks={resources.get('recommended_ntasks', 'n/a')}, "
            f"walltime={resources.get('walltime_hours', 'n/a')}h"
        )
    return lines


def _parameter_summary(rows: list[dict[str, str]], limit: int = 8) -> list[str]:
    if not rows:
        return ["- No parameter rows available."]
    lines = [f"- Total parameters: {len(rows)}"]
    for row in rows[:limit]:
        parameter = row.get("parameter", "")
        value = row.get("value", "")
        if parameter:
            lines.append(f"- {parameter}: {value}")
    if len(rows) > limit:
        lines.append(f"- ... ({len(rows) - limit} more)")
    return lines


def _analysis_summary(analysis_report: dict[str, Any]) -> list[str]:
    status = analysis_report.get("status", "unknown")
    lines = [
        f"- Status: {status}",
        f"- Software: {analysis_report.get('software', 'unknown')}",
        f"- Task: {analysis_report.get('task', 'unknown')}",
        f"- Conclusions: {analysis_report.get('conclusions', 'n/a')}",
    ]
    if status != "completed":
        lines.append("- Note: Analysis outputs are not fully ready; this summary reflects degraded/waiting state.")
    return lines


def _visualization_summary(figures_manifest: dict[str, Any]) -> list[str]:
    status = figures_manifest.get("status", "unknown")
    figures = figures_manifest.get("figures", [])
    lines = [
        f"- Status: {status}",
    ]
    if figures:
        lines.append("- Figures:")
        for figure in figures:
            lines.append(f"  - {figure.get('name', 'unknown')} ({figure.get('title', 'untitled')})")
    else:
        skipped = figures_manifest.get("skipped_reasons", [])
        lines.append("- Figures: none")
        if skipped:
            lines.append(f"- Skipped reasons: {'; '.join(skipped)}")
    if status != "completed":
        lines.append("- Note: Visualization remains degraded or waiting; no finalized figure conclusions are claimed.")
    return lines


def _claim_entry(
    claim_id: str,
    claim: str,
    source_artifact_ids: list[str],
    *,
    status: str,
    evidence_state: str | None = None,
    speculative: bool = False,
) -> dict[str, Any]:
    return {
        "claim_id": claim_id,
        "claim": claim,
        "source_artifact_ids": source_artifact_ids,
        "status": status,
        "evidence_state": evidence_state or status,
        "speculative": speculative,
    }


def _artifact_ids_for(required_artifacts: dict[str, dict[str, Any]], *keys: str) -> list[str]:
    return [
        required_artifacts[key]["artifact_id"]
        for key in keys
        if key in required_artifacts and required_artifacts[key].get("artifact_id")
    ]


def _walk_json_values(payload: Any):
    if isinstance(payload, dict):
        yield payload
        for value in payload.values():
            yield from _walk_json_values(value)
    elif isinstance(payload, list):
        for item in payload:
            yield from _walk_json_values(item)


def _has_status(payload: Any, statuses: set[str]) -> bool:
    for item in _walk_json_values(payload):
        status = item.get("status")
        if isinstance(status, str) and status in statuses:
            return True
    return False


def _has_tracked_only_tool(payload: Any) -> bool:
    for item in _walk_json_values(payload):
        actual_tool = item.get("actual_tool_used")
        if isinstance(actual_tool, dict) and actual_tool.get("support_level") == "tracked_only":
            return True
        if item.get("support_level") == "tracked_only":
            return True
        if item.get("tool_support_level") == "tracked_only":
            return True
    return False


def _conditional_evidence_missing(payload: Any) -> list[str]:
    missing: list[str] = []
    for item in _walk_json_values(payload):
        for key in ("missing_conditional_evidence", "missing_roles"):
            values = item.get(key)
            if isinstance(values, list):
                missing.extend(str(value) for value in values)
        for requirement in item.get("evidence_requirements", []) if isinstance(item.get("evidence_requirements"), list) else []:
            if not isinstance(requirement, dict):
                continue
            if requirement.get("required") is True and requirement.get("present") is False:
                missing.append(str(requirement.get("evidence_key") or requirement.get("role") or "conditional_evidence"))
    return list(dict.fromkeys(missing))


def _blocked_claims_from(payload: Any) -> list[str]:
    blocked: list[str] = []
    for item in _walk_json_values(payload):
        values = item.get("blocked_claims")
        if isinstance(values, list):
            blocked.extend(str(value) for value in values)
    return list(dict.fromkeys(blocked))


def _degraded_evidence_states(
    compute_plan: dict[str, Any],
    analysis_report: dict[str, Any],
    figures_manifest: dict[str, Any],
) -> list[dict[str, Any]]:
    states: list[dict[str, Any]] = []
    if not compute_plan.get("real_submit", False):
        states.append({
            "area": "computation",
            "state": "dry_run_only",
            "severity": "info",
            "claim_policy": "Do not describe the calculation as submitted or completed.",
        })

    for area, payload in (
        ("computation", compute_plan),
        ("analysis", analysis_report),
        ("visualization", figures_manifest),
    ):
        if _has_tracked_only_tool(payload):
            states.append({
                "area": area,
                "state": "tracked_only_provenance",
                "severity": "info",
                "claim_policy": "Write toolchain provenance only; do not claim helper-validated execution or scientific conclusions.",
            })
        if _has_status(payload, {"capability_warning", "waiting"}):
            states.append({
                "area": area,
                "state": "capability_warning_or_waiting",
                "severity": "warning",
                "claim_policy": "Write as pending evidence; do not claim the activity passed or completed.",
            })
        if _has_status(payload, {"skipped_optional_dependency"}):
            states.append({
                "area": area,
                "state": "skipped_optional_dependency",
                "severity": "info",
                "claim_policy": "Record the skipped optional dependency in limitations.",
            })
        missing_conditional = _conditional_evidence_missing(payload)
        if missing_conditional:
            states.append({
                "area": area,
                "state": "conditional_evidence_missing",
                "severity": "warning",
                "claim_policy": "Block or flag claims that require the missing conditional evidence.",
                "missing_evidence": missing_conditional,
                "blocked_claims": _blocked_claims_from(payload),
            })

    analysis_status = analysis_report.get("status", "unknown")
    if analysis_status != "completed":
        states.append({
            "area": "analysis",
            "state": analysis_status,
            "severity": "warning" if analysis_status in {"waiting_for_outputs", "missing_evidence"} else "info",
            "claim_policy": "Do not present analysis-derived conclusions as final results.",
        })

    visualization_status = figures_manifest.get("status", "unknown")
    if visualization_status != "completed":
        states.append({
            "area": "visualization",
            "state": visualization_status,
            "severity": "warning" if visualization_status in {"waiting_for_outputs", "missing_evidence"} else "info",
            "claim_policy": "Do not make finalized figure claims from degraded visualization evidence.",
            "skipped_reasons": figures_manifest.get("skipped_reasons", []),
        })

    visual_qa = figures_manifest.get("visual_qa", {})
    visual_qa_status = visual_qa.get("status") if isinstance(visual_qa, dict) else None
    if visual_qa_status and visual_qa_status not in {"passed", "skipped"}:
        states.append({
            "area": "visual_qa",
            "state": visual_qa_status,
            "severity": "warning" if visual_qa_status == "error" else "info",
            "claim_policy": "Do not treat figure QA as passed.",
        })
    return states


def _degraded_state_lines(states: list[dict[str, Any]]) -> list[str]:
    if not states:
        return ["- None recorded."]
    return [
        f"- {item['area']}: {item['state']} ({item['claim_policy']})"
        for item in states
    ]


def _build_claim_map(
    *,
    contract: dict[str, Any],
    required_artifacts: dict[str, dict[str, Any]],
    structure_manifest: dict[str, Any],
    compute_plan: dict[str, Any],
    analysis_report: dict[str, Any],
    figures_manifest: dict[str, Any],
) -> dict[str, Any]:
    analysis_completed = analysis_report.get("status") == "completed"
    figures_completed = figures_manifest.get("status") == "completed"
    degraded_states = _degraded_evidence_states(compute_plan, analysis_report, figures_manifest)
    blocked_claims = list(dict.fromkeys(
        claim
        for state in degraded_states
        for claim in state.get("blocked_claims", [])
    ))
    compute_state = "dry_run_only" if not compute_plan.get("real_submit") else "submitted_with_record"
    analysis_state = "supported_by_analysis" if analysis_completed else analysis_report.get("status", "waiting_for_outputs")
    figure_state = "supported_by_figures" if figures_completed else figures_manifest.get("status", "no_final_figure_claim")
    proposal_sources = _artifact_ids_for(required_artifacts, "proposal", "research_questions")
    modeling_sources = _artifact_ids_for(required_artifacts, "structure_manifest")
    compute_sources = _artifact_ids_for(required_artifacts, "compute_plan")
    analysis_sources = _artifact_ids_for(required_artifacts, "analysis_report")
    figure_sources = _artifact_ids_for(required_artifacts, "figures_manifest")
    claims = [
        _claim_entry(
            "claim_001",
            f"The writing target addresses: {contract.get('research_goal') or 'the recorded research goal'}.",
            proposal_sources,
            status="supported_by_proposal" if proposal_sources else "missing_evidence",
            evidence_state="supported_by_proposal" if proposal_sources else "missing_evidence",
            speculative=not bool(proposal_sources),
        ),
        _claim_entry(
            "claim_002",
            f"The modeled system is {contract.get('material', 'the recorded material')} with source mode {structure_manifest.get('source_mode', 'unknown')}.",
            modeling_sources,
            status="supported_by_modeling_artifact" if modeling_sources else "missing_evidence",
            evidence_state="supported_by_modeling_artifact" if modeling_sources else "missing_evidence",
            speculative=not bool(modeling_sources),
        ),
        _claim_entry(
            "claim_003",
            "Computation is represented as a dry-run-first package; real submit is not claimed as completed.",
            compute_sources,
            status=("dry_run_evidence_only" if not compute_plan.get("real_submit") else "submitted_with_record")
            if compute_sources
            else "missing_evidence",
            evidence_state=compute_state if compute_sources else "missing_evidence",
            speculative=not bool(compute_sources),
        ),
        _claim_entry(
            "claim_004",
            analysis_report.get("conclusions", "Analysis outputs are not ready."),
            analysis_sources,
            status="supported_by_analysis" if analysis_completed else "waiting_for_outputs",
            evidence_state=analysis_state,
            speculative=not analysis_completed,
        ),
        _claim_entry(
            "claim_005",
            "Figure claims are limited to traceable figures listed in the figures manifest.",
            figure_sources,
            status="supported_by_figures" if figures_completed else "no_final_figure_claim",
            evidence_state=figure_state,
            speculative=not figures_completed,
        ),
    ]
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "claim_policy": "Scientific claims must trace to registered artifacts; incomplete computation or analysis is not written as complete.",
        "source_artifact_ids": list(dict.fromkeys(
            artifact["artifact_id"] for artifact in required_artifacts.values()
            if artifact.get("artifact_id")
        )),
        "analysis_status": analysis_report.get("status"),
        "visualization_status": figures_manifest.get("status"),
        "degraded_evidence_states": degraded_states,
        "unresolved_degraded_state_count": len(degraded_states),
        "blocked_claims": blocked_claims,
        "claims": claims,
    }


def run_writing_stage(workflow_dir: str, params: dict | None = None, dry_run: bool = False) -> dict:
    project_root = resolve_project_root_from_workflow_dir(workflow_dir)
    state = read_state(project_root=str(project_root), state_file="workflow.json")
    if not state:
        return {"status": "error", "message": "No workflow state found"}

    params = params or {}
    metadata = read_state(project_root=str(project_root), state_file="metadata.json")

    try:
        contract = load_proposal_contract(str(project_root / ".simflow"), allow_direct_entry=True)
        required_artifacts = _resolve_required_artifacts(project_root)
    except Exception as exc:
        if not _allows_partial_writing_entry(metadata, state):
            return {"status": "error", "message": str(exc)}
        try:
            contract = load_proposal_contract(str(project_root / ".simflow"), allow_direct_entry=True)
        except Exception:
            contract = {
                "workflow_type": metadata.get("workflow_type", state.get("workflow_type")),
                "software": metadata.get("software"),
                "material": metadata.get("material"),
                "research_goal": metadata.get("research_goal"),
                "parameter_rows": [],
            }
        required_artifacts = {}
        missing_writing_inputs = str(exc)
    else:
        missing_writing_inputs = ""

    parent_artifact_ids = [artifact["artifact_id"] for artifact in required_artifacts.values()]

    if required_artifacts:
        proposal_path = project_root / required_artifacts["proposal"]["path"]
        parameter_table_path = project_root / required_artifacts["parameter_table"]["path"]
        structure_manifest_path = project_root / required_artifacts["structure_manifest"]["path"]
        compute_plan_path = project_root / required_artifacts["compute_plan"]["path"]
        analysis_report_path = project_root / required_artifacts["analysis_report"]["path"]
        figures_manifest_path = project_root / required_artifacts["figures_manifest"]["path"]

        parameter_rows = _read_parameter_rows(parameter_table_path)
        structure_manifest = _read_json(structure_manifest_path)
        compute_plan = _read_json(compute_plan_path)
        analysis_report = _read_json(analysis_report_path)
        figures_manifest = _read_json(figures_manifest_path)
        proposal_reference = _relative_path(project_root, proposal_path)
        writing_input_status = "complete"
    else:
        parameter_rows = contract.get("parameter_rows", [])
        structure_manifest = {
            "source_mode": "not_provided",
            "structure_files": [],
            "validation": {"status": "missing_evidence"},
        }
        compute_plan = {"dry_run": True, "real_submit": False, "task": contract.get("task") or "unknown"}
        analysis_report = {
            "status": "missing_evidence",
            "software": contract.get("software") or "unknown",
            "task": contract.get("task") or "unknown",
            "conclusions": "No analysis artifacts were provided for this direct writing entry.",
        }
        figures_manifest = {
            "status": "missing_evidence",
            "figures": [],
            "skipped_reasons": ["No figures manifest was provided for this direct writing entry."],
        }
        proposal_reference = "not_provided"
        writing_input_status = "partial_missing_upstream_artifacts"

    methods_path = project_root / ".simflow" / "reports" / "writing" / "methods.md"
    results_path = project_root / ".simflow" / "reports" / "writing" / "results.md"
    claim_map_path = project_root / ".simflow" / "reports" / "writing" / "claim_map.json"
    reproducibility_package_path = project_root / ".simflow" / "reports" / "reproducibility" / "reproducibility_package.md"
    reproducibility_manifest_path = project_root / ".simflow" / "reports" / "reproducibility" / "reproducibility_manifest.json"
    final_handoff_markdown_path = project_root / ".simflow" / "reports" / "handoff" / "final_handoff.md"
    final_handoff_json_path = project_root / ".simflow" / "reports" / "handoff" / "final_handoff.json"
    verification_report_path = project_root / ".simflow" / "reports" / "verify" / "verification_report.json"
    methods_rel = _relative_path(project_root, methods_path)
    results_rel = _relative_path(project_root, results_path)
    claim_map_rel = _relative_path(project_root, claim_map_path)
    reproducibility_package_rel = _relative_path(project_root, reproducibility_package_path)
    reproducibility_manifest_rel = _relative_path(project_root, reproducibility_manifest_path)
    final_handoff_markdown_rel = _relative_path(project_root, final_handoff_markdown_path)
    final_handoff_json_rel = _relative_path(project_root, final_handoff_json_path)
    verification_report_rel = _relative_path(project_root, verification_report_path)

    manifest: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "workflow_type": contract.get("workflow_type"),
        "software": contract.get("software"),
        "material": contract.get("material"),
        "analysis_status": analysis_report.get("status"),
        "visualization_status": figures_manifest.get("status"),
        "writing_input_status": writing_input_status,
        "missing_writing_inputs": missing_writing_inputs,
        "source_artifact_ids": parent_artifact_ids,
        "status": "planned" if dry_run else "completed",
        "outputs": [
            methods_rel,
            results_rel,
            claim_map_rel,
            reproducibility_package_rel,
            final_handoff_markdown_rel,
            final_handoff_json_rel,
        ],
        "auxiliary_outputs": [reproducibility_manifest_rel, verification_report_rel],
    }

    if dry_run:
        return {
            "status": "dry_run_complete",
            "manifest": manifest,
            "inputs": parent_artifact_ids,
            "planned_outputs": [
                methods_rel,
                results_rel,
                claim_map_rel,
                reproducibility_package_rel,
                final_handoff_markdown_rel,
                final_handoff_json_rel,
            ],
            "auxiliary_outputs": [reproducibility_manifest_rel, verification_report_rel],
        }

    methods_path.parent.mkdir(parents=True, exist_ok=True)

    methods_content = "\n".join([
        "# Methods",
        "",
        "## Research Goal",
        contract.get("research_goal") or "Not specified.",
        "",
        "## System and Material",
        f"- Material: {contract.get('material', 'Not specified')}",
        "",
        "## Software",
        f"- Software: {contract.get('software', 'unknown')}",
        "",
        "## Modeling Summary",
        *_modeling_summary(structure_manifest),
        "",
        "## Compute Configuration",
        *_compute_summary(compute_plan),
        "",
        "## Parameter Table Summary",
        *_parameter_summary(parameter_rows),
        "",
        "## Source Artifact IDs",
        *(f"- {artifact_id}" for artifact_id in parent_artifact_ids),
        "",
        "## Proposal Reference",
        f"- Path: {proposal_reference}",
    ])
    methods_path.write_text(methods_content, encoding="utf-8")

    degraded_states = _degraded_evidence_states(compute_plan, analysis_report, figures_manifest)
    results_content = "\n".join([
        "# Results",
        "",
        "## Analysis Summary",
        *_analysis_summary(analysis_report),
        "",
        "## Visualization Summary",
        *_visualization_summary(figures_manifest),
        "",
        "## Degraded Evidence States",
        *_degraded_state_lines(degraded_states),
        "",
        "## Traceability / Source Artifact IDs",
        *(f"- {artifact_id}" for artifact_id in parent_artifact_ids),
    ])
    results_path.write_text(results_content, encoding="utf-8")
    claim_map = _build_claim_map(
        contract=contract,
        required_artifacts=required_artifacts,
        structure_manifest=structure_manifest,
        compute_plan=compute_plan,
        analysis_report=analysis_report,
        figures_manifest=figures_manifest,
    )
    claim_map_path.write_text(json.dumps(claim_map, indent=2, ensure_ascii=False), encoding="utf-8")

    methods_artifact = register_artifact(
        "methods.md",
        "methods",
        "writing",
        project_root=str(project_root),
        path=methods_rel,
        parent_artifacts=parent_artifact_ids,
        parameters={
            "software": contract.get("software"),
            "material": contract.get("material"),
            "analysis_status": analysis_report.get("status"),
            "visualization_status": figures_manifest.get("status"),
        },
        software=contract.get("software"),
    )
    results_artifact = register_artifact(
        "results.md",
        "results",
        "writing",
        project_root=str(project_root),
        path=results_rel,
        parent_artifacts=[methods_artifact["artifact_id"], *parent_artifact_ids],
        parameters={
            "software": contract.get("software"),
            "material": contract.get("material"),
            "analysis_status": analysis_report.get("status"),
            "visualization_status": figures_manifest.get("status"),
        },
        software=contract.get("software"),
    )
    claim_map_artifact = register_artifact(
        "claim_map.json",
        "claim_map",
        "writing",
        project_root=str(project_root),
        path=claim_map_rel,
        parent_artifacts=[methods_artifact["artifact_id"], results_artifact["artifact_id"], *parent_artifact_ids],
        parameters={
            "claim_count": len(claim_map["claims"]),
            "analysis_status": analysis_report.get("status"),
            "visualization_status": figures_manifest.get("status"),
        },
        software=contract.get("software"),
        metadata={"evidence_key": "claim_traceability"},
    )
    reproducibility_result = BUILD_REPRODUCIBILITY_PACKAGE(
        str(project_root / ".simflow"),
        parent_artifact_ids=[
            methods_artifact["artifact_id"],
            results_artifact["artifact_id"],
            claim_map_artifact["artifact_id"],
            *parent_artifact_ids,
        ],
        software=contract.get("software"),
        write_manifest_json=True,
    )
    if reproducibility_result.get("status") != "success":
        return {"status": "error", "message": "Failed to build reproducibility package"}

    reproducibility_manifest_artifact = next(
        artifact for artifact in reproducibility_result["artifacts"] if artifact["name"] == "reproducibility_manifest.json"
    )
    reproducibility_package_artifact = next(
        artifact for artifact in reproducibility_result["artifacts"] if artifact["name"] == "reproducibility_package.md"
    )
    final_handoff_result = GENERATE_FINAL_HANDOFF(
        str(project_root / ".simflow"),
        source_artifact_ids=parent_artifact_ids,
        parent_artifact_ids=[
            methods_artifact["artifact_id"],
            results_artifact["artifact_id"],
            claim_map_artifact["artifact_id"],
            reproducibility_package_artifact["artifact_id"],
            reproducibility_manifest_artifact["artifact_id"],
            *parent_artifact_ids,
        ],
        software=contract.get("software"),
    )
    if final_handoff_result.get("status") != "success":
        return {"status": "error", "message": "Failed to build final handoff deliverables"}

    verification_parent_artifact_ids = [
        methods_artifact["artifact_id"],
        results_artifact["artifact_id"],
        claim_map_artifact["artifact_id"],
        reproducibility_package_artifact["artifact_id"],
        reproducibility_manifest_artifact["artifact_id"],
        *(artifact["artifact_id"] for artifact in final_handoff_result["artifacts"]),
        *parent_artifact_ids,
    ]
    verification_result = VERIFY_WORKFLOW(
        str(project_root / ".simflow"),
        params={
            "parent_artifact_ids": verification_parent_artifact_ids,
            "source_artifact_ids": parent_artifact_ids,
            "software": contract.get("software"),
        },
        dry_run=False,
    )
    if verification_result.get("status") != "success":
        return {"status": "error", "message": "Failed to build verification report"}

    manifest["verification_status"] = verification_result.get("verification_status")
    manifest["verification_report"] = verification_report_rel
    if verification_result.get("verification_status") in {"warning", "fail"}:
        manifest["status"] = "completed_with_warnings"

    return {
        "status": "success",
        "artifacts": [
            methods_artifact,
            results_artifact,
            claim_map_artifact,
            reproducibility_package_artifact,
            *final_handoff_result["artifacts"],
        ],
        "manifest": manifest,
        "inputs": parent_artifact_ids,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the canonical writing stage")
    parser.add_argument("--workflow-dir", required=True, help="Path to .simflow directory")
    parser.add_argument("--params", type=str, default="{}", help="JSON parameters for the stage")
    parser.add_argument("--dry-run", action="store_true", default=False)
    args = parser.parse_args()

    try:
        params = json.loads(args.params)
        result = run_writing_stage(args.workflow_dir, params=params, dry_run=args.dry_run)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except Exception as exc:
        print(json.dumps({"status": "error", "message": str(exc)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
