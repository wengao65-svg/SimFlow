# SimFlow Technical Design

## Architecture Overview

```
┌─────────────────────────────────────────────┐
│              Codex/OMX Host                  │
├─────────────────────────────────────────────┤
│  Skills Layer (23 skills)                   │
│  ├── simflow-modeling (structure/I/O)       │
│  ├── simflow-dft (DFT workflow)             │
│  ├── simflow-aimd (AIMD workflow)           │
│  └── simflow-md (MD workflow)               │
├─────────────────────────────────────────────┤
│  Workflow Layer (9 stages)                  │
│  ├── Stage definitions & dependencies       │
│  ├── Gates (9 verification gates)           │
│  └── Policies (6 policies)                  │
├─────────────────────────────────────────────┤
│  MCP Servers (4 servers)                    │
│  ├── literature (arXiv/Crossref/S2)         │
│  ├── structure (MP/COD)                     │
│  ├── hpc (SLURM/PBS/SSH/Local)             │
│  └── state (workflow state management)      │
├─────────────────────────────────────────────┤
│  Runtime Layer                              │
│  ├── lib/ (state, artifact, hpc utilities)  │
│  └── scripts/ (validation, checkpointing)   │
├─────────────────────────────────────────────┤
│  .simflow/ State Directory                  │
│  ├── state/ (workflow, stage, job, artifact)│
│  ├── artifacts/ (simulation outputs)        │
│  └── extensions/ (custom skills)            │
└─────────────────────────────────────────────┘
```

## Data Flow

1. User invokes a skill (e.g., `simflow-dft:run_relax`)
2. Skill reads current state from `.simflow/state/`
3. Skill executes computation (generate inputs, run analysis)
4. Results written to `.simflow/artifacts/`
5. State updated with new stage/artifact references
6. Verification gate checks pass/fail criteria
7. Workflow advances to next stage

## Component Relationships

- **Skills** are self-contained modules with defined contracts (SKILL.md)
- **Stages** bind skills to workflow positions with input/output contracts
- **Gates** enforce verification between stages
- **Policies** enforce workflow-wide constraints
- **MCP Servers** provide external system access via tool-based interface
- **State** is the single source of truth for workflow progress

## Technology Stack

- Python 3.10+ for runtime and skills
- pymatgen for crystal structure manipulation
- ASE for atomistic structure I/O
- MDAnalysis for trajectory analysis
- JSON Schema (draft-07) for validation
- MCP protocol for external service communication
