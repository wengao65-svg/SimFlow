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
    name="relaxed_structure",
    artifact_type="structure",
    stage="relax",
    base_dir=".simflow/artifacts"
)
```

## Lineage Tracking

Each artifact records its provenance:

```json
{
  "name": "relaxed_structure",
  "type": "structure",
  "stage": "relax",
  "path": ".simflow/artifacts/relaxed_structure.cif",
  "lineage": {
    "inputs": ["initial_structure"],
    "parameters": {
      "encut": 520,
      "ediff": 1e-6,
      "ibrion": 2
    },
    "software": "vasp",
    "version": "6.3.0"
  }
}
```

## Versioning

Artifacts are versioned by stage execution. Multiple runs of the same stage produce versioned artifacts:

```
.artifacts/
├── relaxed_structure.cif        # Latest
├── relaxed_structure_v1.cif     # First run
└── relaxed_structure_v2.cif     # Second run
```

## Artifact Validation

Each artifact type has validation rules defined in `schemas/artifact.json`:
- File must exist at declared path
- File format must match declared type
- File size must be non-zero
- Required metadata fields must be present
