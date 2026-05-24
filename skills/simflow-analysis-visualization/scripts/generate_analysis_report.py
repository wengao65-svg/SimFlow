#!/usr/bin/env python3
"""Generate analysis report from DFT/MD results.

Reads analysis results and renders them into the analysis_report.md template.
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

TEMPLATE_PATH = Path(__file__).resolve().parents[3] / "templates" / "reports" / "analysis_report.md.template"


def render_template(template_content: str, variables: dict) -> str:
    """Render a Jinja-style template with {{ variable }} placeholders."""
    result = template_content
    for key, value in variables.items():
        pattern = r"\{\{\s*" + re.escape(key) + r"\s*(?:\|[^}]*)?\}\}"
        result = re.sub(pattern, str(value) if value is not None else "N/A", result)
    return result


def generate_report(analysis_results: dict, output_path: str) -> dict:
    """Generate an analysis report markdown file."""
    if not TEMPLATE_PATH.exists():
        raise FileNotFoundError(f"Template not found: {TEMPLATE_PATH}")

    template = TEMPLATE_PATH.read_text()

    # Build template variables from analysis results
    variables = {
        "workflow_id": analysis_results.get("workflow_id", "unknown"),
        "stage": analysis_results.get("stage", "analysis"),
        "timestamp": datetime.now().isoformat(),
        "software": analysis_results.get("software", "unknown"),
        "final_energy": analysis_results.get("final_energy"),
        "energy_converged": analysis_results.get("energy_converged", "N/A"),
        "energy_change": analysis_results.get("energy_change"),
        "max_force": analysis_results.get("max_force"),
        "force_converged": analysis_results.get("force_converged", "N/A"),
        "stress": analysis_results.get("stress"),
        "optimization_steps": analysis_results.get("optimization_steps"),
        "structural_change": analysis_results.get("structural_change"),
        "total_energy": analysis_results.get("total_energy"),
        "formation_energy": analysis_results.get("formation_energy"),
        "band_gap": analysis_results.get("band_gap"),
        "fermi_level": analysis_results.get("fermi_level"),
        "trajectory_steps": analysis_results.get("trajectory_steps"),
        "temperature": analysis_results.get("temperature"),
        "pressure": analysis_results.get("pressure"),
        "msd": analysis_results.get("msd"),
        "diffusion_coefficient": analysis_results.get("diffusion_coefficient"),
        "rdf_analysis": analysis_results.get("rdf_analysis", "No RDF analysis performed."),
        "bond_analysis": analysis_results.get("bond_analysis", "No bond analysis performed."),
        "conclusions": analysis_results.get("conclusions", "No conclusions provided."),
    }

    # Handle figures loop (simplified - replace for-loop section)
    figures = analysis_results.get("figures", [])
    figures_section = ""
    for fig in figures:
        figures_section += f"\n### {fig.get('title', 'Figure')}\n"
        figures_section += f"![{fig.get('caption', '')}]({fig.get('path', '')})\n"
    if not figures_section:
        figures_section = "No figures generated."

    # Handle reference data loop
    ref_data = analysis_results.get("reference_data", [])
    ref_section = ""
    for ref in ref_data:
        ref_section += f"| {ref.get('property', '')} | {ref.get('calculated', '')} | "
        ref_section += f"{ref.get('literature', '')} | {ref.get('deviation', '')} |\n"
    if not ref_section:
        ref_section = "| - | - | - | - |\n"

    content = render_template(template, variables)

    # Replace for-loop sections manually (templates use {% for %} syntax)
    content = re.sub(
        r"\{%\s*for figure in figures\s*%\}.*?\{%\s*endfor\s*%\}",
        figures_section, content, flags=re.DOTALL
    )
    content = re.sub(
        r"\{%\s*for ref in reference_data\s*%\}.*?\{%\s*endfor\s*%\}",
        ref_section, content, flags=re.DOTALL
    )

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(content)

    return {
        "status": "success",
        "output": str(out),
        "sections": ["convergence", "energy", "trajectory", "structure", "visualization", "conclusions"],
    }


def main():
    parser = argparse.ArgumentParser(description="Generate analysis report")
    parser.add_argument("--results", required=True, help="JSON file with analysis results")
    parser.add_argument("--output", default="analysis_report.md", help="Output report path")
    args = parser.parse_args()

    try:
        with open(args.results) as f:
            results = json.load(f)
        report = generate_report(results, args.output)
        print(json.dumps(report, indent=2))
    except Exception as e:
        print(json.dumps({"status": "error", "message": str(e)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
