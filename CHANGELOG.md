# Changelog

## v0.5.0 (2026-05-03)

### Added
- **Batch 9: Schemas** — 7 JSON schemas for workflow, stage, skill-contract, mcp-capability, custom-skill-binding, state, hpc-job validation
- **Batch 9: Fixtures** — 3 test fixtures (vasprun.xml, QE output, LAMMPS dump) for unit tests
- **Batch 10: Skill Tests** — 7 unit test files for build_structure, make_supercell, validate_structure, generate_vasp_inputs, analyze_md_trajectory, prepare_job, plot_energy_curve
- **Batch 10: Workflow Tests** — 3 test files for stage definitions, workflow definitions, gates/policies
- **Batch 10: MCP Tests** — 3 test files for state server, artifact server, mock connectors
- **Batch 11: Literature Connectors** — arxiv (Atom feed), crossref (REST), semantic_scholar (REST with S2_API_KEY)
- **Batch 11: Structure Connectors** — materials_project (REST with MP_API_KEY), cod (REST, no key needed)
- **Batch 11: HPC Connectors** — pbs (qsub/qstat/qdel), local (subprocess), ssh (SCP+SSH)
- **Batch 11: Credentials** — mcp/shared/credentials.py with env-only storage, sanitize_for_logging
- **Batch 12: Documentation** — 13 docs: PRD, technical-design, workflow-layer, skill-design, mcp-design, state-and-checkpoint, artifact-schema, verification-gates, hpc-integration, custom-skills, user-guide, software-skills, credentials-policy
- **Batch 12: Examples** — 3 workflow examples (DFT, AIMD, MD)
- **Batch 12: Scaffolds** — 2 scaffold scripts (skill, stage)

### Fixed
- BCC structure building: corrected species count from 1 to 2 for 2-atom BCC cell
- validate_structure: fixed PeriodicNeighbor `in` operator TypeError by using getattr

### Changed
- MCP servers now support multiple backends with auto-detection and fallback
- HPC server gained `submit` tool in addition to `dry_run`, `prepare`, `status`
- Literature server: `backend` parameter for arxiv/crossref/semantic_scholar selection
- Structure server: `backend` parameter for materials_project/cod selection

## v0.4.0 (2026-04-30)

### Added
- Phase 11-12: E2E tests (3 files), workflow templates, .simflow template
- Phase 10: Runtime library (state, artifact, hpc, checkpoint utilities)
- Phase 9: MCP servers (literature, structure, hpc, state) with mock connectors
- Phase 8: Hooks, gates, policies definitions

## v0.3.0 (2026-04-27)

### Added
- Phase 6-7: Domain skills (simflow-modeling) and software skills (simflow-dft, simflow-aimd, simflow-md)
- 23 skill scripts: structure building, input generation, analysis, plotting, job preparation
- Notification templates for workflow events

## v0.2.0 (2026-04-24)

### Added
- Phase 3-5: Workflow definitions (3 workflows), stage definitions (9 stages)
- Agent definitions (9 agents)
- Skill contracts (SKILL.md files)

## v0.1.0 (2026-04-21)

### Added
- Phase 0-2: Project scaffold, plugin manifest, schema foundation
- Initial directory structure
- metadata.json, plugin.json
- Base schemas (artifact.json)
