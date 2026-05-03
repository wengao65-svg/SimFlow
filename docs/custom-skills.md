# Custom Skills Guide

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

Custom skills bind to workflow stages via `stage_binding`. When a custom skill declares the same stage as a built-in skill, the custom skill takes priority.

## Discovery Order

1. `.simflow/extensions/skills/` (custom, highest priority)
2. `skills/` (built-in)

## Best Practices

- Keep scripts focused on a single task
- Declare all inputs/outputs in SKILL.md
- Use relative paths for output files
- Handle missing inputs gracefully
- Include docstrings for complex analysis steps
