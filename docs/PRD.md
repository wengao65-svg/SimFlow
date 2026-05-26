# SimFlow Product Requirements Document

## Product Overview

SimFlow is a Codex-native computational simulation workflow layer for agentic
research. It records stages, evidence, artifacts, lineage, checkpoints, safety
gates, and handoff context around open computational work.

SimFlow is not a centralized workflow executor. Codex, Claude Code, or another
host agent remains responsible for scientific reasoning, literature selection,
modeling choices, simulation software, analysis code, and writing format.

## Target Users

- Computational simulation researchers who need traceable research state.
- Agentic coding users who need safe handoff across literature, modeling,
  computation, analysis, and writing.
- Teams that need dry-run-first local, remote, or HPC submission discipline.

## Core Capabilities

1. **Workflow-layer state**: project `.simflow/` state, canonical stages,
   recipes/tags, and handoff summaries.
2. **Artifact and lineage tracking**: registered literature, model, compute,
   analysis, figure, and writing artifacts with metadata and checksums.
3. **Evidence-based gates**: dry-run, validation, credential scan, approval, and
   hash checks before real local, remote, or HPC submit.
4. **Optional helpers**: supported domain assistants for VASP, CP2K, and
   LAMMPS, plus generic parsers, templates, and analysis utilities. QE and
   Gaussian are reserved placeholders in the current product build.
5. **Skill and MCP integration**: canonical skills and MCP recording tools
   expose the workflow layer to host agents without a central executor.

## Feature Matrix

| Feature | Current position |
| --- | --- |
| Literature review | Evidence tracking; no required source/provider |
| Proposal | Traceable plan and resource/risk evidence |
| Modeling | Preserve user-provided models and transformations |
| Computation | Dry-run-first setup, validation, hash evidence, gated submit |
| Analysis/visualization | Built-in or self-written helpers, all recorded with lineage |
| Writing | Claim-to-evidence traceability; no fixed document structure |
| DFT/AIMD/MD | Reference recipes/tags |
| Supported engine helpers | VASP, CP2K, and LAMMPS domain assistants, not workflow executors |
| Unsupported placeholders | QE and Gaussian; user-provided files may be tracked as generic artifacts |

## Success Criteria

- Users can enter SimFlow from any canonical research stage.
- Scientific claims trace to literature, model, computation, analysis, or figure
  artifacts.
- Real local, remote, or HPC execution is blocked without approval, dry-run
  evidence, credential scan, and matching hashes.
- Unknown engine tasks return uncertainty and missing information instead of
  being forced into a default task.
- Current projects use canonical stages and open recipe/tag metadata instead of
  fixed DFT/AIMD/MD workflow types.
