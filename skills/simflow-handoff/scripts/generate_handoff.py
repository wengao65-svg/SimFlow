#!/usr/bin/env python3
"""Generate workflow handoff summary.

Produces a comprehensive summary of workflow progress, artifacts,
checkpoints, and next steps for handoff between sessions or team members.
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from runtime.lib.state import read_state
from runtime.lib.checkpoint import list_checkpoints
from runtime.lib.utils import generate_id

TEMPLATE_PATH = Path(__file__).resolve().parents[3] / "templates" / "reports" / "handoff.md.template"


def render_template(template_content: str, variables: dict) -> str:
    """Render a Jinja-style template."""
    result = template_content
    for key, value in variables.items():
        pattern = r"\{\{\s*" + re.escape(key) + r"\s*(?:\|[^}]*)?\}\}"
        result = re.sub(pattern, str(value) if value is not None else "N/A", result)
    return result


def generate_handoff(workflow_dir: str, output_file: str = None) -> dict:
    """Generate handoff summary."""
    wf_dir = Path(workflow_dir)
    state = read_state(str(wf_dir))

    if not state:
        return {"status": "error", "message": "No workflow state found"}

    # Read metadata
    metadata_path = wf_dir / "metadata.json"
    metadata = json.loads(metadata_path.read_text()) if metadata_path.exists() else {}

    # Get checkpoints
    checkpoints = list_checkpoints(str(wf_dir))

    # Build stage status
    stages = state.get("stages", [])
    stage_states = state.get("stage_states", {})
    completed = [s for s in stages if stage_states.get(s) == "completed"]
    in_progress = [s for s in stages if stage_states.get(s) == "in_progress"]
    failed = [s for s in stages if stage_states.get(s) == "failed"]

    # Collect artifacts
    artifacts = []
    artifacts_dir = wf_dir / "artifacts"
    if artifacts_dir.exists():
        for art_file in artifacts_dir.glob("*.json"):
            try:
                artifacts.append(json.loads(art_file.read_text()))
            except json.JSONDecodeError:
                pass

    handoff = {
        "handoff_id": generate_id("handoff"),
        "workflow_id": state.get("workflow_id", "unknown"),
        "workflow_type": metadata.get("workflow_type", "unknown"),
        "generated_at": datetime.now().isoformat(),
        "status": state.get("status", "unknown"),
        "current_stage": state.get("current_stage", "unknown"),
        "completed_stages": completed,
        "in_progress_stages": in_progress,
        "failed_stages": failed,
        "total_stages": len(stages),
        "progress_pct": round(len(completed) / max(len(stages), 1) * 100, 1),
        "artifacts_count": len(artifacts),
        "checkpoints_count": len(checkpoints),
        "latest_checkpoint": checkpoints[-1] if checkpoints else None,
        "metadata": metadata,
    }

    # Generate markdown if template exists
    if output_file and TEMPLATE_PATH.exists():
        template = TEMPLATE_PATH.read_text()

        variables = {
            "generated_at": handoff["generated_at"],
            "workflow_id": handoff["workflow_id"],
            "workflow_type": handoff["workflow_type"],
            "status": handoff["status"],
            "checkpoint_id": handoff["latest_checkpoint"]["checkpoint_id"] if handoff["latest_checkpoint"] else "N/A",
            "checkpoint_stage": handoff["latest_checkpoint"]["stage"] if handoff["latest_checkpoint"] else "N/A",
            "checkpoint_time": handoff["latest_checkpoint"]["created_at"] if handoff["latest_checkpoint"] else "N/A",
            "needs_approval": len(failed) > 0,
        }

        content = render_template(template, variables)

        # Handle for-loops
        completed_section = "\n".join("- [x] " + s for s in completed) or "None"
        content = re.sub(r"\{%\s*for stage in completed_stages\s*%\}.*?\{%\s*endfor\s*%\}",
                         completed_section, content, flags=re.DOTALL)

        in_progress_section = "\n".join("- [ ] " + s + " (进行中)" for s in in_progress) or "None"
        content = re.sub(r"\{%\s*for stage in in_progress_stages\s*%\}.*?\{%\s*endfor\s*%\}",
                         in_progress_section, content, flags=re.DOTALL)

        failed_section = "\n".join("- [!] " + s for s in failed) or "None"
        content = re.sub(r"\{%\s*for stage in failed_stages\s*%\}.*?\{%\s*endfor\s*%\}",
                         failed_section, content, flags=re.DOTALL)

        content = re.sub(r"\{%\s*for stage, artifacts in artifacts_by_stage.items\(\)\s*%\}.*?\{%\s*endfor\s*%\}",
                         "See artifacts directory", content, flags=re.DOTALL)

        content = re.sub(r"\{%\s*for verification in verifications\s*%\}.*?\{%\s*endfor\s*%\}",
                         "Pending", content, flags=re.DOTALL)

        content = re.sub(r"\{%\s*for risk in risks\s*%\}.*?\{%\s*endfor\s*%\}",
                         "- Review failed stages before proceeding", content, flags=re.DOTALL)

        content = re.sub(r"\{%\s*for step in next_steps\s*%\}.*?\{%\s*endfor\s*%\}",
                         "- Resume from: {}".format(handoff["current_stage"]), content, flags=re.DOTALL)

        content = re.sub(r"\{%\s*for action in approval_actions\s*%\}.*?\{%\s*endfor\s*%\}",
                         "- Review and approve failed stages", content, flags=re.DOTALL)

        out = Path(output_file)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(content)
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
