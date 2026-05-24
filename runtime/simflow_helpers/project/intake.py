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

from runtime.simflow_core.literature import empty_research_source_inputs, normalize_research_sources
from runtime.simflow_core.state import init_workflow, write_state
from runtime.simflow_core.workflow import compatibility_activity_sequence, load_recipe


def load_workflow_definition(workflow_type: str) -> dict:
    """Load workflow metadata from canonical recipes."""
    normalized = (workflow_type or "dft").lower()
    try:
        recipe = load_recipe(normalized, include_legacy=False)
    except FileNotFoundError:
        recipe = load_recipe("dft", include_legacy=False)
        normalized = "dft"
    stages = recipe.get("stages", [])
    if not isinstance(stages, list) or not stages:
        raise ValueError(f"Workflow {normalized} has no stages")
    activities = compatibility_activity_sequence(stages)
    recipe_source = recipe.get("legacy_source", {})
    return {
        "workflow_type": normalized,
        "path": recipe_source.get("path"),
        "name": recipe.get("name", normalized),
        "stages": stages,
        "canonical_stages": stages,
        "compatibility_activities": activities,
        "stage_dependencies": {},
        "entry_points": stages,
        "default_entry": stages[0],
    }



def parse_inline_values(value: str) -> list[str]:
    """Parse comma-delimited or JSON-array inline values."""
    stripped = value.strip()
    if not stripped:
        return []
    if stripped.startswith("["):
        loaded = json.loads(stripped)
        if isinstance(loaded, list):
            return [str(item).strip() for item in loaded if str(item).strip()]
        return [str(loaded).strip()]
    return [item.strip() for item in stripped.replace(";", ",").split(",") if item.strip()]



def parse_inline_notes(value: str) -> list[str]:
    """Parse inline manual notes without splitting prose text."""
    stripped = value.strip()
    if not stripped:
        return []
    if stripped.startswith("["):
        loaded = json.loads(stripped)
        if isinstance(loaded, list):
            return [str(item).strip() for item in loaded if str(item).strip()]
        return [str(loaded).strip()]
    return [stripped]



def parse_inline_source_objects(value: str) -> list[dict]:
    """Parse JSON source objects for explicit research-source declarations."""
    stripped = value.strip()
    if not stripped:
        return []
    loaded = json.loads(stripped)
    if isinstance(loaded, dict):
        return [loaded]
    if isinstance(loaded, list):
        return loaded
    raise ValueError("sources must be a JSON object or array")



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
        "source_inputs": empty_research_source_inputs(),
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
            elif key in ("pdf", "pdfs", "paper", "papers"):
                result["source_inputs"]["pdf"].extend(parse_inline_values(value))
            elif key in ("bib", "bibtex", "references", "reference_files"):
                result["source_inputs"]["bibtex"].extend(parse_inline_values(value))
            elif key in ("doi", "dois"):
                result["source_inputs"]["doi"].extend(parse_inline_values(value))
            elif key in ("note", "notes", "manual_note", "manual_notes"):
                result["source_inputs"]["note"].extend(parse_inline_notes(value))
            elif key in ("sources", "research_sources"):
                result["source_inputs"]["sources"].extend(parse_inline_source_objects(value))

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
    research_sources = normalize_research_sources(
        parsed.get("source_inputs"),
        project_root=output_dir,
    )

    metadata = {
        "workflow_id": workflow_id,
        "workflow_type": wf_type,
        "workflow_name": workflow["name"],
        "recipe_definition": workflow["path"],
        "entry_point": entry_point,
        "entry_points": workflow["entry_points"],
        "stage_dependencies": workflow["stage_dependencies"],
        "stages": stages,
        "compatibility_activities": workflow["compatibility_activities"],
        "current_stage": entry_point,
        "research_goal": parsed["research_goal"],
        "material": parsed["material"],
        "software": parsed.get("software", "vasp"),
        "parameters": parsed.get("parameters", {}),
        "research_sources": research_sources,
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
