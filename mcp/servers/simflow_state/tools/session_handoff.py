"""Tool: Generate a session-level handoff report.

Produces a compact handoff summary that captures the current workflow state,
latest checkpoint, artifact counts, and any warnings (orphan compute, risky
directories, stale state). The report is written to
.simflow/reports/session_handoff_<timestamp>.md.
"""

from datetime import datetime, timezone

from runtime.simflow_core.state import (
    ProjectRootError,
    read_state,
    resolve_project_root,
    ensure_simflow_dir,
    write_report,
)


def _project_root(params: dict) -> str:
    project_root = params.get("project_root")
    if not project_root:
        raise ProjectRootError("project_root is required for MCP read operations")
    return project_root


def execute(params: dict) -> dict:
    """Generate a session handoff report.

    The report includes:
    - Workflow ID, type, current stage, status
    - Latest checkpoint ID and timestamp
    - Artifact, checkpoint, gate, job counts
    - Stage statuses
    - Engagement status (tools called in session)
    - Warnings (stale state, missing stages)
    """
    try:
        project_root = _project_root(params)
        root = resolve_project_root(project_root=project_root)
    except ProjectRootError as error:
        return {"status": "error", "message": str(error)}

    ensure_simflow_dir(project_root=str(root))
    now = datetime.now(timezone.utc).isoformat()
    timestamp_short = now.replace(":", "").replace("-", "")[:15]

    # Read all state files
    wf = read_state(project_root=str(root), state_file="workflow.json") or {}
    stages = read_state(project_root=str(root), state_file="stages.json") or {}
    artifacts = read_state(project_root=str(root), state_file="artifacts.json")
    artifact_count = len(artifacts) if isinstance(artifacts, list) else 0
    checkpoints = read_state(project_root=str(root), state_file="checkpoints.json")
    checkpoint_list = checkpoints if isinstance(checkpoints, list) else []
    gates = read_state(project_root=str(root), state_file="gates.json")
    gate_count = len(gates) if isinstance(gates, list) else 0
    jobs = read_state(project_root=str(root), state_file="jobs.json")
    job_count = len(jobs) if isinstance(jobs, list) else 0
    verification = read_state(project_root=str(root), state_file="verification.json")
    verification_count = len(verification) if isinstance(verification, list) else 0

    # Get engagement status
    engagement_status = {}
    try:
        from runtime.simflow_core.engagement import get_engagement_status
        engagement_status = get_engagement_status(str(root))
    except Exception:
        pass

    # Latest checkpoint
    latest_ckpt = None
    if checkpoint_list:
        latest_ckpt = checkpoint_list[-1] if isinstance(checkpoint_list[-1], dict) else None

    # Detect stale state
    warnings = []
    wf_updated = wf.get("updated_at", "")
    if latest_ckpt and wf_updated:
        ckpt_created = latest_ckpt.get("created_at", "")
        if ckpt_created and ckpt_created > wf_updated:
            warnings.append(
                f"State may be stale: workflow.json updated_at ({wf_updated}) "
                f"is older than latest checkpoint ({ckpt_created})"
            )

    # Detect missing canonical stages
    canonical_stages = [
        "literature_review", "proposal", "modeling",
        "computation", "analysis_visualization", "writing",
    ]
    declared_stages = set(stages.keys()) if isinstance(stages, dict) else set()
    missing_stages = [s for s in canonical_stages if s not in declared_stages]
    if missing_stages:
        warnings.append(f"Canonical stages not declared: {', '.join(missing_stages)}")

    # Detect empty gates/jobs despite having checkpoints
    if len(checkpoint_list) > 0 and gate_count == 0:
        warnings.append(
            f"{len(checkpoint_list)} checkpoints exist but gates.json is empty — "
            f"compute may have run without gate approval"
        )

    # Build report
    lines = [
        f"# Session Handoff — {timestamp_short}",
        "",
        f"Generated: {now}",
        f"Project root: {root}",
        "",
        "## Workflow State",
        "",
        f"- Workflow ID: {wf.get('workflow_id', 'unknown')}",
        f"- Workflow type: {wf.get('workflow_type', 'unknown')}",
        f"- Current stage: {wf.get('current_stage', 'unknown')}",
        f"- Status: {wf.get('status', 'unknown')}",
        f"- Updated: {wf.get('updated_at', 'unknown')}",
        "",
        "## Latest Checkpoint",
        "",
    ]
    if latest_ckpt:
        lines.extend([
            f"- Checkpoint ID: {latest_ckpt.get('checkpoint_id', 'unknown')}",
            f"- Stage: {latest_ckpt.get('stage_id', 'unknown')}",
            f"- Status: {latest_ckpt.get('status', 'unknown')}",
            f"- Created: {latest_ckpt.get('created_at', 'unknown')}",
            f"- Description: {latest_ckpt.get('description', '')}",
        ])
    else:
        lines.append("(no checkpoints)")

    lines.extend([
        "",
        "## Counts",
        "",
        f"- Artifacts: {artifact_count}",
        f"- Checkpoints: {len(checkpoint_list)}",
        f"- Gates: {gate_count}",
        f"- Jobs: {job_count}",
        f"- Verification records: {verification_count}",
        "",
    ])

    # Stage statuses
    if isinstance(stages, dict) and stages:
        lines.extend(["## Stage Status", ""])
        for stage_name in canonical_stages:
            stage = stages.get(stage_name)
            if isinstance(stage, dict):
                lines.append(f"- {stage_name}: {stage.get('status', 'pending')}")
        for stage_name, stage in sorted(stages.items()):
            if stage_name not in canonical_stages and isinstance(stage, dict):
                lines.append(f"- {stage_name}: {stage.get('status', 'pending')}")
        lines.append("")

    # Engagement status
    if engagement_status:
        lines.extend([
            "## Session Engagement",
            "",
            f"- Has active session: {engagement_status.get('has_session', False)}",
            f"- Session start: {engagement_status.get('session_start', 'N/A')}",
            f"- Last activity: {engagement_status.get('last_activity', 'N/A')}",
            f"- Tools called: {', '.join(engagement_status.get('tools_called_in_session', []))}",
            "",
        ])

    # Warnings
    if warnings:
        lines.extend(["## Warnings", ""])
        for w in warnings:
            lines.append(f"- {w}")
        lines.append("")

    # Next steps
    lines.extend([
        "## Suggested Next Steps",
        "",
    ])
    if not latest_ckpt:
        lines.append("- Create a checkpoint to save current progress")
    if gate_count == 0 and job_count > 0:
        lines.append("- Record gate decisions for existing compute jobs")
    if missing_stages:
        lines.append(f"- Declare missing stages: {', '.join(missing_stages)}")
    if not warnings:
        lines.append("- State is consistent — continue with next research task")
    lines.append("")

    report_content = "\n".join(lines)
    report_file = f"session_handoff_{timestamp_short}.md"
    write_report(report_content, project_root=str(root), report_file=report_file)

    return {
        "status": "success",
        "project_root": str(root),
        "data": {
            "report_path": f".simflow/reports/{report_file}",
            "workflow_id": wf.get("workflow_id", "unknown"),
            "current_stage": wf.get("current_stage", "unknown"),
            "latest_checkpoint": latest_ckpt.get("checkpoint_id") if latest_ckpt else None,
            "artifact_count": artifact_count,
            "checkpoint_count": len(checkpoint_list),
            "gate_count": gate_count,
            "job_count": job_count,
            "warnings": warnings,
        },
    }
