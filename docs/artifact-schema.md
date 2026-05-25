# Artifact Schema

## Artifact Types

| Type | Description | Formats |
|------|-------------|---------|
| `structure` | Crystal/molecular structure | CIF, POSCAR, XYZ, PDB |
| `input` | Simulation input file | INCAR, KPOINTS, pw.in, lammps.in |
| `output` | Simulation output | vasprun.xml, qe.out, log.lammps |
| `trajectory` | MD trajectory | XTC, TRR, DCD, dump.lammps |
| `data` | Numerical data | JSON, CSV, NPY |
| `plot` | Visualization | PNG, SVG, PDF |
| `report` | Analysis report | JSON, MD |

## Artifact Registration

Artifacts are registered via the artifact MCP server:

```python
register_artifact(
    name="structure.cif",
    artifact_type="structure",
    stage="modeling",
    project_root="/path/to/project",
    path="models/structure.cif",
    metadata={"source": "user_provided_or_transformed"}
)
```

## Lineage Tracking

Each artifact records its provenance:

```json
{
  "name": "energy_curve.png",
  "type": "figure",
  "stage": "analysis_visualization",
  "path": "figures/energy_curve.png",
  "checksum": "sha256:...",
  "metadata": {
    "caption_status": "draft",
    "speculative": false
  },
  "lineage": {
    "parent_artifacts": ["art_analysis_table", "art_plot_script"],
    "parameters": {
      "x": "volume",
      "y": "energy"
    },
    "software": "matplotlib"
  }
}
```

Artifact records should use canonical stage names. Helper activity details such
as input generation or figure rendering belong in artifact metadata, not as
top-level stage names.

## Versioning

Artifacts are versioned by registration history. Multiple records with the same
name receive incremented versions while retaining lineage:

```text
.simflow/state/artifacts.json
  structure.cif v1.0.0
  structure.cif v2.0.0
```

## Artifact Validation

Each artifact type has validation rules defined in `schemas/artifact.json`:

- file must exist at declared path when a path is provided
- file size should be non-zero for file artifacts
- metadata should describe source and stage context
- lineage should link derived artifacts to source artifacts where possible

Common artifact types are examples, not a closed enum. Custom artifact types are
allowed when their metadata and lineage are clear.
