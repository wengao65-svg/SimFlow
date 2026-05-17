# Skills Design

## Skill Contract (SKILL.md)

Every skill declares a contract in its SKILL.md file:

```yaml
skill_name: simflow-dft:run_relax
stage_binding: relax
inputs:
  - name: structure
    type: file
    format: cif
  - name: encut
    type: number
    default: 520
outputs:
  - name: relaxed_structure
    type: file
    format: cif
  - name: energy
    type: number
mcp_tools:
  - hpc:submit
  - hpc:dry_run
```

## Skill Structure

```
skills/
└── simflow-dft/
    ├── SKILL.md
    ├── metadata.json
    ├── scripts/
    │   ├── run_relax.py
    │   ├── run_scf.py
    │   └── run_bands.py
    └── templates/
        ├── INCAR.relax
        └── KPOINTS.mesh
```

## Binding Rules

1. A skill maps to exactly one stage
2. Stage inputs must be a subset of skill inputs
3. Skill outputs must satisfy stage expected outputs
4. MCP tool dependencies must be declared

## Custom Skills

Users can create custom skills in `.simflow/extensions/skills/`:

```
.simflow/
└── extensions/
    └── skills/
        └── my-custom-analysis/
            ├── SKILL.md
            └── scripts/
                └── analyze.py
```

Custom skills override built-in skills when they declare the same `stage_binding`.

## Skill Discovery

Skills are discovered by scanning:
1. `skills/` directory (built-in)
2. `.simflow/extensions/skills/` (custom, highest priority)
