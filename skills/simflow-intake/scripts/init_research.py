#!/usr/bin/env python3
"""Initialize a new research workflow from user input.

Parses user requirements (material, method, goals) and initializes
the .simflow/ directory structure with workflow state.
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from runtime.lib.state import init_workflow, write_state


WORKFLOWS_DIR = Path(__file__).resolve().parents[3] / "workflow" / "workflows"


def load_workflow_definition(workflow_type: str) -> dict:
    """Load the canonical workflow definition for a workflow type."""
    normalized = (workflow_type or "dft").lower()
    path = WORKFLOWS_DIR / f"{normalized}.json"
    if not path.exists():
        path = WORKFLOWS_DIR / "dft.json"
        normalized = "dft"
    data = json.loads(path.read_text(encoding="utf-8"))
    stages = data.get("stages", [])
    if not isinstance(stages, list) or not stages:
        raise ValueError(f"Workflow {normalized} has no stages")
    return {
        "workflow_type": normalized,
        "path": str(path),
        "name": data.get("name", normalized),
        "stages": [stage["name"] if isinstance(stage, dict) else stage for stage in stages],
        "stage_dependencies": data.get("stage_dependencies", {}),
        "entry_points": data.get("entry_points", []),
        "default_entry": data.get("default_entry") or data.get("entry_point") or (
            stages[0]["name"] if isinstance(stages[0], dict) else stages[0]
        ),
    }



def parse_research_input(input_text: str) -> dict:
    """Parse structured research input text into components."""
    lines = input_text.strip().split("\n")
    result = {
        "research_goal": "",
        "material": "",
        "method": "",
        "software": "vasp",
        "workflow_type": "dft",
        "parameters": {},
    }

    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line:
            key, _, value = line.partition(":")
            key = key.strip().lower()
            value = value.strip()
            if key in ("goal", "research_goal", "objective"):
                result["research_goal"] = value
            elif key in ("material", "system", "structure"):
                result["material"] = value
            elif key in ("method", "workflow_type", "type"):
                result["workflow_type"] = value.lower()
                result["method"] = value
            elif key in ("software", "code"):
                result["software"] = value.lower()
            elif key in ("parameters", "params"):
                try:
                    result["parameters"] = json.loads(value)
                except json.JSONDecodeError:
                    result["parameters"] = {"raw": value}

    return result


def init_research(input_file: str = None, input_text: str = None,
                  workflow_type: str = None, output_dir: str = ".") -> dict:
    """Initialize a new research workflow."""
    if input_file:
        content = Path(input_file).read_text(encoding="utf-8")
        parsed = parse_research_input(content)
    elif input_text:
        parsed = parse_research_input(input_text)
    else:
        parsed = {
            "research_goal": "New research",
            "workflow_type": "dft",
            "software": "vasp",
            "material": "unknown",
            "parameters": {},
        }

    if workflow_type:
        parsed["workflow_type"] = workflow_type

    workflow = load_workflow_definition(parsed.get("workflow_type", "dft"))
    wf_type = workflow["workflow_type"]
    stages = workflow["stages"]
    entry_point = workflow["default_entry"]

    state = init_workflow(wf_type, entry_point, project_root=output_dir)
    workflow_id = state["workflow_id"]
    project_dir = Path(output_dir) / ".simflow"

    metadata = {
        "workflow_id": workflow_id,
        "workflow_type": wf_type,
        "workflow_name": workflow["name"],
        "workflow_definition": workflow["path"],
        "entry_point": entry_point,
        "entry_points": workflow["entry_points"],
        "stage_dependencies": workflow["stage_dependencies"],
        "stages": stages,
        "current_stage": entry_point,
        "research_goal": parsed["research_goal"],
        "material": parsed["material"],
        "software": parsed.get("software", "vasp"),
        "parameters": parsed.get("parameters", {}),
        "created_at": datetime.now().isoformat(),
    }
    write_state(metadata, project_root=output_dir, state_file="metadata.json")

    return {
        "status": "success",
        "workflow_id": workflow_id,
        "workflow_type": wf_type,
        "project_dir": str(project_dir),
        "stages": stages,
        "current_stage": entry_point,
        "metadata": metadata,
    }


def main():
    parser = argparse.ArgumentParser(description="Initialize research workflow")
    parser.add_argument("--input", dest="input_file", help="Input file with research requirements")
    parser.add_argument("--text", dest="input_text", help="Inline research description")
    parser.add_argument("--type", dest="workflow_type",
                        choices=["dft", "aimd", "md"], help="Workflow type")
    parser.add_argument("--output-dir", default=".", help="Output directory")
    args = parser.parse_args()

    try:
        result = init_research(args.input_file, args.input_text,
                               args.workflow_type, args.output_dir)
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(json.dumps({"status": "error", "message": str(e)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
