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

from runtime.lib.state import init_workflow
from runtime.lib.utils import generate_id, safe_filename


DEFAULT_STAGES = {
    "dft": ["proposal", "literature_review", "modeling", "input_generation",
            "compute", "analysis", "visualization", "writing", "review"],
    "aimd": ["proposal", "literature_review", "modeling", "input_generation",
             "compute", "analysis", "visualization", "writing", "review"],
    "md": ["proposal", "literature_review", "modeling", "input_generation",
           "compute", "analysis", "visualization", "writing", "review"],
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
    # Parse input
    if input_file:
        content = Path(input_file).read_text()
        parsed = parse_research_input(content)
    elif input_text:
        parsed = parse_research_input(input_text)
    else:
        parsed = {"research_goal": "New research", "workflow_type": "dft",
                  "software": "vasp", "material": "unknown", "parameters": {}}

    if workflow_type:
        parsed["workflow_type"] = workflow_type

    wf_type = parsed["workflow_type"]
    if wf_type not in DEFAULT_STAGES:
        wf_type = "dft"

    # Generate workflow ID
    workflow_id = generate_id("wf")
    project_dir = Path(output_dir) / ".simflow"
    project_dir.mkdir(parents=True, exist_ok=True)

    # Initialize workflow state
    stages = DEFAULT_STAGES[wf_type]
    state = init_workflow(
        workflow_id=workflow_id,
        workflow_type=wf_type,
        stages=stages,
        project_dir=str(project_dir),
    )

    # Write research metadata
    metadata = {
        "workflow_id": workflow_id,
        "workflow_type": wf_type,
        "research_goal": parsed["research_goal"],
        "material": parsed["material"],
        "software": parsed.get("software", "vasp"),
        "parameters": parsed.get("parameters", {}),
        "created_at": datetime.now().isoformat(),
        "stages": stages,
        "current_stage": stages[0],
    }
    (project_dir / "metadata.json").write_text(json.dumps(metadata, indent=2))

    return {
        "status": "success",
        "workflow_id": workflow_id,
        "workflow_type": wf_type,
        "project_dir": str(project_dir),
        "stages": stages,
        "current_stage": stages[0],
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
