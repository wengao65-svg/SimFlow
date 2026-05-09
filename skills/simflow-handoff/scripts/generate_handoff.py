#!/usr/bin/env python3
"""Generate workflow handoff summary.

Produces a comprehensive summary of workflow progress, artifacts,
checkpoints, and next steps for handoff between sessions or team members.
"""

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from runtime.lib.state import read_state
from runtime.lib.utils import generate_id

TEMPLATE_PATH = Path(__file__).resolve().parents[3] / "templates" / "reports" / "handoff.md.template"
WORKFLOWS_DIR = Path(__file__).resolve().parents[3] / "workflow" / "workflows"


def render_template(template_content: str, variables: dict) -> str:
    """Render a Jinja-style template."""
    result = template_content
    for key, value in variables.items():
        pattern = r"\{\{\s*" + re.escape(key) + r"\s*(?:\|[^}]*)?\}\}"
        result = re.sub(pattern, str(value) if value is not None else "N/A", result)
    return result


def resolve_project_root_from_workflow_dir(workflow_dir: str) -> Path:
    """Resolve the project root from either a project root or .simflow path."""
    path = Path(workflow_dir).expanduser().resolve()
    return path.parent if path.name == ".simflow" else path


def load_workflow_stages(workflow_type: str, metadata: dict) -> list[str]:
    """Load canonical workflow stages from metadata or workflow definitions."""
    stages = metadata.get("stages", [])
    if isinstance(stages, list) and stages:
        return stages

    normalized = (workflow_type or "dft").lower()
    path = WORKFLOWS_DIR / f"{normalized}.json"
    if not path.exists():
        path = WORKFLOWS_DIR / "dft.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    loaded = data.get("stages", [])
    return [stage["name"] if isinstance(stage, dict) else stage for stage in loaded]


def group_artifacts_by_stage(artifacts: list[dict]) -> dict[str, list[dict]]:
    """Group artifact registry records by stage."""
    grouped: dict[str, list[dict]] = {}
    for artifact in artifacts:
        stage = artifact.get("stage", "unknown")
        grouped.setdefault(stage, []).append(artifact)
    return grouped


def ordered_stage_names(stage_names: list[str], stage_registry: dict, status: str) -> list[str]:
    """Return stage names in workflow order filtered by status."""
    return [stage for stage in stage_names if stage_registry.get(stage, {}).get("status") == status]


def build_pending_stages(stage_names: list[str], stage_registry: dict) -> list[str]:
    """Return stage names that are still pending in workflow order."""
    return [
        stage for stage in stage_names
        if stage_registry.get(stage, {}).get("status", "pending") == "pending"
    ]


def generate_handoff(workflow_dir: str, output_file: str = None) -> dict:
    """Generate handoff summary from canonical workflow registries."""
    project_root = resolve_project_root_from_workflow_dir(workflow_dir)
    workflow = read_state(project_root=str(project_root), state_file="workflow.json")

    if not workflow:
        return {"status": "error", "message": "No workflow state found"}

    metadata = read_state(project_root=str(project_root), state_file="metadata.json")
    stage_registry = read_state(project_root=str(project_root), state_file="stages.json")
    artifacts = read_state(project_root=str(project_root), state_file="artifacts.json")
    checkpoints = read_state(project_root=str(project_root), state_file="checkpoints.json")

    workflow_type = metadata.get("workflow_type", workflow.get("workflow_type", "dft"))
    stage_names = load_workflow_stages(workflow_type, metadata)
    completed = ordered_stage_names(stage_names, stage_registry, "completed")
    in_progress = ordered_stage_names(stage_names, stage_registry, "in_progress")
    failed = ordered_stage_names(stage_names, stage_registry, "failed")
    pending = build_pending_stages(stage_names, stage_registry)
    artifacts_by_stage = group_artifacts_by_stage(artifacts if isinstance(artifacts, list) else [])
    latest_checkpoint = checkpoints[-1] if isinstance(checkpoints, list) and checkpoints else None

    risks = []
    if failed:
        risks.append(f"Failed stages: {', '.join(failed)}")
    if latest_checkpoint is None:
        risks.append("No checkpoints exist")

    next_steps = []
    if failed:
        next_steps.append(f"Retry stage: {failed[0]}")
    elif in_progress:
        next_steps.append(f"Continue stage: {in_progress[0]}")
    elif pending:
        next_steps.append(f"Start stage: {pending[0]}")
    else:
        next_steps.append("Workflow complete")

    handoff = {
        "handoff_id": generate_id("handoff"),
        "workflow_id": workflow.get("workflow_id", metadata.get("workflow_id", "unknown")),
        "workflow_type": workflow_type,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": workflow.get("status", "unknown"),
        "current_stage": workflow.get("current_stage", metadata.get("current_stage", "unknown")),
        "plan_reference": workflow.get("plan"),
        "completed_stages": completed,
        "in_progress_stages": in_progress,
        "failed_stages": failed,
        "pending_stages": pending,
        "total_stages": len(stage_names),
        "progress_pct": round(len(completed) / max(len(stage_names), 1) * 100, 1),
        "artifacts_count": len(artifacts if isinstance(artifacts, list) else []),
        "artifacts_by_stage": artifacts_by_stage,
        "checkpoints_count": len(checkpoints) if isinstance(checkpoints, list) else 0,
        "latest_checkpoint": latest_checkpoint,
        "metadata": metadata,
        "risks": risks,
        "next_steps": next_steps,
        "needs_approval": bool(failed),
    }

    if output_file and TEMPLATE_PATH.exists():
        template = TEMPLATE_PATH.read_text(encoding="utf-8")

        variables = {
            "generated_at": handoff["generated_at"],
            "workflow_id": handoff["workflow_id"],
            "workflow_type": handoff["workflow_type"],
            "status": handoff["status"],
            "checkpoint_id": latest_checkpoint["checkpoint_id"] if latest_checkpoint else "N/A",
            "checkpoint_stage": latest_checkpoint["stage_id"] if latest_checkpoint else "N/A",
            "checkpoint_time": latest_checkpoint["created_at"] if latest_checkpoint else "N/A",
            "needs_approval": handoff["needs_approval"],
        }

        content = render_template(template, variables)

        completed_section = "\n".join("- [x] " + stage for stage in completed) or "None"
        content = re.sub(
            r"\{%\s*for stage in completed_stages\s*%\}.*?\{%\s*endfor\s*%\}",
            completed_section,
            content,
            flags=re.DOTALL,
        )

        in_progress_section = "\n".join("- [ ] " + stage + " (进行中)" for stage in in_progress) or "None"
        content = re.sub(
            r"\{%\s*for stage in in_progress_stages\s*%\}.*?\{%\s*endfor\s*%\}",
            in_progress_section,
            content,
            flags=re.DOTALL,
        )

        failed_section = "\n".join("- [!] " + stage for stage in failed) or "None"
        content = re.sub(
            r"\{%\s*for stage in failed_stages\s*%\}.*?\{%\s*endfor\s*%\}",
            failed_section,
            content,
            flags=re.DOTALL,
        )

        artifact_sections = []
        for stage in stage_names:
            stage_artifacts = artifacts_by_stage.get(stage, [])
            if not stage_artifacts:
                continue
            rows = [
                f"| {artifact['artifact_id']} | {artifact['name']} | {artifact['type']} | {artifact['version']} |"
                for artifact in stage_artifacts
            ]
            artifact_sections.append(
                "\n".join([
                    f"### {stage}",
                    "| 产物 ID | 名称 | 类型 | 版本 |",
                    "|---------|------|------|------|",
                    *rows,
                ])
            )
        content = re.sub(
            r"\{%\s*for stage, artifacts in artifacts_by_stage.items\(\)\s*%\}.*?\{%\s*endfor\s*%\}",
            "\n\n".join(artifact_sections) or "None",
            content,
            flags=re.DOTALL,
        )

        content = re.sub(
            r"\{%\s*for verification in verifications\s*%\}.*?\{%\s*endfor\s*%\}",
            "Pending",
            content,
            flags=re.DOTALL,
        )

        risks_section = "\n".join("- " + risk for risk in risks) or "- None"
        content = re.sub(
            r"\{%\s*for risk in risks\s*%\}.*?\{%\s*endfor\s*%\}",
            risks_section,
            content,
            flags=re.DOTALL,
        )

        next_steps_section = "\n".join("- " + step for step in next_steps) or "- None"
        content = re.sub(
            r"\{%\s*for step in next_steps\s*%\}.*?\{%\s*endfor\s*%\}",
            next_steps_section,
            content,
            flags=re.DOTALL,
        )

        approval_actions = [f"Review failed stage: {stage}" for stage in failed]
        approval_section = "\n".join("- [ ] " + action for action in approval_actions) or "无需审批"
        content = re.sub(
            r"\{%\s*for action in approval_actions\s*%\}.*?\{%\s*endfor\s*%\}",
            approval_section,
            content,
            flags=re.DOTALL,
        )
        content = re.sub(r"\{%\s*if needs_approval\s*%\}|\{%\s*else\s*%\}|\{%\s*endif\s*%\}", "", content)

        content += "\n\n## Backbone Summary\n\n"
        content += f"- Current stage: {handoff['current_stage']}\n"
        content += f"- Pending stages: {', '.join(pending) if pending else 'None'}\n"
        content += f"- Artifact count: {handoff['artifacts_count']}\n"
        content += f"- Plan reference: {handoff['plan_reference'] or 'None'}\n"

        out = Path(output_file)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(content, encoding="utf-8")
        handoff["output_file"] = str(out)

    return {
        "status": "success",
        "handoff": handoff,
    }


def main():
    parser = argparse.ArgumentParser(description="Generate workflow handoff summary")
    parser.add_argument("--workflow-dir", required=True, help="Path to .simflow directory")
    parser.add_argument("--output", help="Output markdown file path")
    args = parser.parse_args()

    try:
        result = generate_handoff(args.workflow_dir, args.output)
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(json.dumps({"status": "error", "message": str(e)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
