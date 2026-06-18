# Custom Skills Guide

Custom skills are project-local extensions. They may add a new activity, domain
helper, or analysis script, or they may override/supplement a built-in
`simflow-*` skill through an explicit binding file. These are separate
contracts:

- `SKILL.md` frontmatter follows `schemas/skill-contract.schema.json`.
- `metadata.json` follows `schemas/custom-skill-metadata.schema.json`.
- Built-in skill override/extend/disable bindings follow
  `schemas/custom-skill-binding.schema.json`.

Custom `stage_binding` values may be canonical stages such as
`analysis_visualization`, or project-local activity/domain labels such as
`analysis`, `rdf`, or `postprocess`. A custom label is metadata for discovery
and routing; it does not redefine SimFlow's top-level stage list.

## Creating a Custom Skill

### Directory Structure

```
.simflow/
└── extensions/
    └── skills/
        └── my-custom-analysis/
            ├── SKILL.md          # Skill contract
            ├── metadata.json     # Skill metadata
            └── scripts/
                └── analyze.py    # Implementation
```

### SKILL.md Contract

```yaml
skill_name: my-custom-analysis:run_analysis
description: Custom RDF analysis with publication-quality plots
stage_binding: analysis
inputs:
  - name: trajectory
    type: file
    format: xtc
  - name: selection
    type: string
    default: "name O"
outputs:
  - name: rdf_plot
    type: file
    format: png
  - name: rdf_data
    type: file
    format: csv
mcp_tools: []
```

### metadata.json

```json
{
  "name": "my-custom-analysis",
  "version": "1.0.0",
  "description": "Custom RDF analysis with publication-quality plots",
  "author": "researcher@university.edu",
  "stage_binding": "analysis"
}
```

### Script Implementation

```python
#!/usr/bin/env python3
"""Custom RDF analysis script."""

import MDAnalysis as mda
from MDAnalysis.analysis.rdf import InterRDF
import matplotlib.pyplot as plt

def run(trajectory, topology, selection="name O", output_dir="."):
    u = mda.Universe(topology, trajectory)
    oxygen = u.select_atoms(selection)
    rdf = InterRDF(oxygen, oxygen)
    rdf.run()

    plt.figure(figsize=(8, 6))
    plt.plot(rdf.results.bins, rdf.results.rdf)
    plt.xlabel("Distance (Å)")
    plt.ylabel("g(r)")
    plt.savefig(f"{output_dir}/rdf_plot.png", dpi=300)
    return {"rdf_plot": f"{output_dir}/rdf_plot.png"}

if __name__ == "__main__":
    import sys
    run(sys.argv[1], sys.argv[2])
```

## Binding to Stages

Custom skills bind to workflow stages, activities, or domain labels via
`stage_binding`.

- Use a canonical stage when the custom skill is intended to participate in a
  built-in stage boundary, for example `analysis_visualization`.
- Use a project-local label when the skill is narrower than a canonical stage,
  for example `analysis` or `rdf`.
- Do not treat project-local labels as new top-level workflow stages unless the
  project also defines the surrounding workflow contract and evidence rules.

When a custom skill is meant to override, extend, or disable a built-in
`simflow-*` skill, declare that separately with a binding document validated by
`schemas/custom-skill-binding.schema.json`. A metadata-only custom skill does
not automatically override a built-in skill.

## Discovery Order

1. `.simflow/extensions/skills/` (custom, highest priority)
2. `skills/` (built-in)

## Best Practices

- Keep scripts focused on a single task
- Declare all inputs/outputs in SKILL.md
- Use relative paths for output files
- Handle missing inputs gracefully
- Include docstrings for complex analysis steps
