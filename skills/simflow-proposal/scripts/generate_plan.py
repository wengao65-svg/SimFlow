#!/usr/bin/env python3
"""Generate a structured research plan from workflow metadata.

Reads the workflow state and metadata, then produces a structured
research plan with stages, parameters, and resource estimates.
"""

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from runtime.lib.state import read_state, write_state
from runtime.lib.utils import generate_id

TEMPLATE_PATH = Path(__file__).resolve().parents[3] / "templates" / "reports" / "proposal.md.template"
PLAN_FILE = "workflow_plan.json"


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


def generate_plan(workflow_dir: str, output_file: str = None) -> dict:
    """Generate research plan from canonical workflow state."""
    project_root = resolve_project_root_from_workflow_dir(workflow_dir)
    simflow_dir = project_root / ".simflow"
    metadata = read_state(project_root=str(project_root), state_file="metadata.json")
    state = read_state(project_root=str(project_root), state_file="workflow.json")

    if not state:
        return {"status": "error", "message": "No workflow state found"}

    stages = metadata.get("stages", [])
    if not stages:
        return {"status": "error", "message": "No stages defined"}

    plan = {
        "plan_id": generate_id("plan"),
        "workflow_id": state.get("workflow_id", metadata.get("workflow_id", "unknown")),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "research_goal": metadata.get("research_goal", "Not specified"),
        "material": metadata.get("material", "Not specified"),
        "software": metadata.get("software", "vasp"),
        "workflow_type": metadata.get("workflow_type", state.get("workflow_type", "dft")),
        "current_stage": state.get("current_stage", metadata.get("current_stage", "unknown")),
        "entry_point": metadata.get("entry_point", state.get("entry_point")),
        "stages": [],
        "parameters": metadata.get("parameters", {}),
    }

    for stage_name in stages:
        plan["stages"].append({
            "name": stage_name,
            "status": "pending",
            "tasks": _get_stage_tasks(stage_name, plan["workflow_type"]),
        })

    plans_dir = simflow_dir / "plans"
    plans_dir.mkdir(parents=True, exist_ok=True)
    plan_path = plans_dir / PLAN_FILE
    plan_path.write_text(json.dumps(plan, indent=2, ensure_ascii=False), encoding="utf-8")

    plan_ref = plan_path.relative_to(simflow_dir).as_posix()
    state["plan"] = plan_ref
    state["updated_at"] = datetime.now(timezone.utc).isoformat()
    write_state(state, project_root=str(project_root), state_file="workflow.json")
    plan["plan_file"] = plan_ref

    if output_file and TEMPLATE_PATH.exists():
        template = TEMPLATE_PATH.read_text(encoding="utf-8")
        params_list = []
        for key, value in plan["parameters"].items():
            params_list.append({"name": key, "value": str(value), "description": ""})

        variables = {
            "research_goal": plan["research_goal"],
            "material_description": plan["material"],
            "chemical_formula": metadata.get("chemical_formula", "N/A"),
            "space_group": metadata.get("space_group", "N/A"),
            "lattice_parameters": metadata.get("lattice_parameters", "N/A"),
            "software": plan["software"],
            "estimated_time": metadata.get("estimated_time", "TBD"),
            "nodes": metadata.get("nodes", "TBD"),
            "memory": metadata.get("memory", "TBD"),
            "control_groups": metadata.get("control_groups", "None specified"),
        }

        content = render_template(template, variables)

        params_section = ""
        for param in params_list:
            params_section += "| {} | {} | {} |\n".format(param["name"], param["value"], param["description"])
        content = re.sub(
            r"\{%\s*for param in parameters\s*%\}.*?\{%\s*endfor\s*%\}",
            params_section,
            content,
            flags=re.DOTALL,
        )

        outputs_section = "\n".join("- " + output for output in metadata.get("expected_outputs", ["TBD"]))
        content = re.sub(
            r"\{%\s*for output in expected_outputs\s*%\}.*?\{%\s*endfor\s*%\}",
            outputs_section,
            content,
            flags=re.DOTALL,
        )

        risks_section = "\n".join("- " + risk for risk in metadata.get("risks", ["None identified"]))
        content = re.sub(
            r"\{%\s*for risk in risks\s*%\}.*?\{%\s*endfor\s*%\}",
            risks_section,
            content,
            flags=re.DOTALL,
        )

        approvals_section = "\n".join("- [ ] " + approval for approval in metadata.get("approval_points", ["None"]))
        content = re.sub(
            r"\{%\s*for approval in approval_points\s*%\}.*?\{%\s*endfor\s*%\}",
            approvals_section,
            content,
            flags=re.DOTALL,
        )

        out = Path(output_file)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(content, encoding="utf-8")
        plan["output_file"] = str(out)

    return {
        "status": "success",
        "plan": plan,
    }


def _get_stage_tasks(stage_name: str, workflow_type: str) -> list:
    """Get default tasks for a workflow stage."""
    task_map = {
        "literature": ["Search relevant papers", "Extract key parameters", "Identify reference data"],
        "review": ["Synthesize prior results", "Compare candidate methods", "Define decision criteria"],
        "proposal": ["Define research objectives", "Identify material system", "Select computational method"],
        "modeling": ["Build crystal structure", "Validate structure", "Generate supercell if needed"],
        "input_generation": ["Configure calculation parameters", "Generate input files", "Validate inputs"],
        "compute": ["Prepare job script", "Submit calculation", "Monitor progress"],
        "analysis": ["Parse output files", "Check convergence", "Extract key metrics"],
        "visualization": ["Plot energy curves", "Generate RDF/MSD plots", "Create summary figures"],
        "writing": ["Generate analysis report", "Compile results", "Draft conclusions"],
    }
    return task_map.get(stage_name, ["Define tasks", "Execute tasks", "Verify results"])


def main():
    parser = argparse.ArgumentParser(description="Generate research plan")
    parser.add_argument("--workflow-dir", required=True, help="Path to .simflow directory")
    parser.add_argument("--output", help="Output markdown file path")
    args = parser.parse_args()

    try:
        result = generate_plan(args.workflow_dir, args.output)
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(json.dumps({"status": "error", "message": str(e)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
