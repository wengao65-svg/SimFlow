#!/usr/bin/env python3
"""Generate a structured research plan from workflow metadata.

Reads the workflow state and metadata, then produces a structured
research plan with stages, parameters, and resource estimates.
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from runtime.lib.utils import generate_id

TEMPLATE_PATH = Path(__file__).resolve().parents[3] / "templates" / "reports" / "proposal.md.template"


def render_template(template_content: str, variables: dict) -> str:
    """Render a Jinja-style template."""
    result = template_content
    for key, value in variables.items():
        pattern = r"\{\{\s*" + re.escape(key) + r"\s*(?:\|[^}]*)?\}\}"
        result = re.sub(pattern, str(value) if value is not None else "N/A", result)
    return result


def generate_plan(workflow_dir: str, output_file: str = None) -> dict:
    """Generate research plan from workflow state."""
    wf_dir = Path(workflow_dir)

    # Read metadata
    metadata_path = wf_dir / "metadata.json"
    if metadata_path.exists():
        metadata = json.loads(metadata_path.read_text())
    else:
        metadata = {}

    # Read workflow state
    state_path = wf_dir / "workflow_state.json"
    if state_path.exists():
        state = json.loads(state_path.read_text())
    else:
        state = {}

    # Build plan
    plan = {
        "plan_id": generate_id("plan"),
        "workflow_id": metadata.get("workflow_id", "unknown"),
        "created_at": datetime.now().isoformat(),
        "research_goal": metadata.get("research_goal", "Not specified"),
        "material": metadata.get("material", "Not specified"),
        "software": metadata.get("software", "vasp"),
        "workflow_type": metadata.get("workflow_type", "dft"),
        "stages": [],
        "parameters": metadata.get("parameters", {}),
    }

    # Build stage details
    stages = state.get("stages", metadata.get("stages", []))
    for stage_name in stages:
        stage_info = {
            "name": stage_name,
            "status": "pending",
            "tasks": _get_stage_tasks(stage_name, metadata.get("workflow_type", "dft")),
        }
        plan["stages"].append(stage_info)

    # Generate markdown if template exists
    if output_file and TEMPLATE_PATH.exists():
        template = TEMPLATE_PATH.read_text()
        params_list = []
        for k, v in plan["parameters"].items():
            params_list.append({"name": k, "value": str(v), "description": ""})

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

        # Handle for-loops
        params_section = ""
        for p in params_list:
            params_section += "| {} | {} | {} |\n".format(p["name"], p["value"], p["description"])
        content = re.sub(
            r"\{%\s*for param in parameters\s*%\}.*?\{%\s*endfor\s*%\}",
            params_section, content, flags=re.DOTALL
        )

        outputs_section = "\n".join("- " + o for o in metadata.get("expected_outputs", ["TBD"]))
        content = re.sub(
            r"\{%\s*for output in expected_outputs\s*%\}.*?\{%\s*endfor\s*%\}",
            outputs_section, content, flags=re.DOTALL
        )

        risks_section = "\n".join("- " + r for r in metadata.get("risks", ["None identified"]))
        content = re.sub(
            r"\{%\s*for risk in risks\s*%\}.*?\{%\s*endfor\s*%\}",
            risks_section, content, flags=re.DOTALL
        )

        approvals_section = "\n".join("- [ ] " + a for a in metadata.get("approval_points", ["None"]))
        content = re.sub(
            r"\{%\s*for approval in approval_points\s*%\}.*?\{%\s*endfor\s*%\}",
            approvals_section, content, flags=re.DOTALL
        )

        out = Path(output_file)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(content)
        plan["output_file"] = str(out)

    return {
        "status": "success",
        "plan": plan,
    }


def _get_stage_tasks(stage_name: str, workflow_type: str) -> list:
    """Get default tasks for a workflow stage."""
    task_map = {
        "proposal": ["Define research objectives", "Identify material system", "Select computational method"],
        "literature_review": ["Search relevant papers", "Extract key parameters", "Identify reference data"],
        "modeling": ["Build crystal structure", "Validate structure", "Generate supercell if needed"],
        "input_generation": ["Configure calculation parameters", "Generate input files", "Validate inputs"],
        "compute": ["Prepare job script", "Submit calculation", "Monitor progress"],
        "analysis": ["Parse output files", "Check convergence", "Extract key metrics"],
        "visualization": ["Plot energy curves", "Generate RDF/MSD plots", "Create summary figures"],
        "writing": ["Generate analysis report", "Compile results", "Draft conclusions"],
        "review": ["Verify results", "Check reproducibility", "Final approval"],
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
