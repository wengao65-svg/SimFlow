# Changelog

## v0.12.0 (2026-08-01) — State-store consolidation

- Reduced the public MCP surface from four servers to two: `simflow_state`
  and `hpc`.
- Moved artifact registration/list/get and checkpoint create/list/restore tools
  into `simflow_state` with explicit canonical tool names.
- Preserved the old `artifact_store` and `checkpoint_store` servers as
  unconfigured compatibility shims for one release cycle.
- Kept runtime artifact/checkpoint APIs and persisted `.simflow/` formats
  unchanged.
- Updated engagement enforcement, host configurations, tests, and user-facing
  tool references for the consolidated state server.

## v0.11.0 (2026-08-01) — MCP surface consolidation

- Reduced the public SimFlow MCP surface from seven servers to four:
  `simflow_state`, `artifact_store`, `checkpoint_store`, and `hpc`.
- Moved literature connector selection, caching, retry, and metadata enrichment
  into `runtime/simflow_helpers/literature`; removed the literature MCP server.
- Removed the structure and parser MCP servers. Structure construction and
  output parsing remain owned by skills and runtime helpers.
- Added per-call SSH `target` binding for HPC upload, download, submit, and
  status operations, including host, user, and port validation without secret
  material in MCP payloads.
- Bound SSH targets and remote work directories to transfer fingerprints,
  transfer approvals, verified manifests, and `hpc_submit` gate decisions.
- Added engagement protection for `hpc/submit` and normalized failed dry-run
  validation to a top-level error response.
- Synchronized Codex, Claude Code, and OpenCode MCP configuration and
  validation around the four-server surface.

## v0.10.0 (2026-07-31) — OpenCode plugin distribution

- Added the dependency-free OpenCode plugin adapter for stable OpenCode 1.18.x.
- Added `opencode-simflow` npm package build, validation, isolated smoke, and
  manual release automation.
- OpenCode now discovers all canonical SimFlow skills and the seven existing
  MCP servers without changing providers, permissions, or safety policy.
- Added OpenCode-specific MCP `clientInfo` guidance and host-adaptation tests.
- Updated installation, developer, limitation, and release documentation for
  the third supported host distribution.

## v0.9.1 (2026-07-28) — Domain-skill analysis boundary remediation

Domain skills owned analysis/plotting helpers that crossed into
`simflow-analysis-visualization` territory. The LAMMPS skill shipped
`analyze_lammps_trajectory.py` (RDF/MSD/diffusion) and the VASP skill shipped
`plot_band_structure.py` (matplotlib rendering), both contradicting their own
declared boundaries. This release returns property analysis and figure
construction to the analysis_visualization stage and establishes an explicit
script-allowlist rule.

### LAMMPS — remove analysis helper, add intake adapter
- Deleted `skills/simflow-lammps/scripts/analyze_lammps_trajectory.py` and
  `tests/skills/test_lammps_analyze_trajectory.py`. RDF/MSD/diffusion no longer
  live under a domain skill.
- New `skills/simflow-lammps/scripts/parse_lammps_outputs.py`: output INTAKE
  adapter mirroring `parse_cp2k_outputs.py`. Parses `log.lammps` thermo via the
  shared `LAMMPSParser` and scans dump/data headers for columns, units style,
  atom ids, image flags, frame count, box bounds, and masses; emits a
  `lammps_output_intake_manifest` and handoff artifact. Computes no property
  claims.
- Updated `SKILL.md` and `references/lammps_output_intake.md` to describe the
  new intake adapter and the analysis-stage boundary.

### analysis_visualization — strengthened MD trajectory helper
- `skills/simflow-analysis-visualization/scripts/analyze_md_trajectory.py`
  rewritten: single load-once `Universe` (was reloading per analysis);
  migrated `build_analysis_quality_manifest`; `--equilibration-start` now
  actually slices RDF/MSD (was recorded but ignored); units-aware diffusion
  conversion (cm²/s emitted only when `--timestep-units ps`, null otherwise to
  avoid silent lj/si unit errors); `--topology-format`/`--trajectory-format`
  pass-through (fixes LAMMPS data+dump loading); `EinsteinMSD` FFT fallback to
  `fft=False` when `tidynamics` is unavailable; unified schema key
  `diffusion_coefficient_*`.
- Added `--topology-format`/`--trajectory-format` CLI args.

### VASP — move plotting to analysis_visualization
- Moved `skills/simflow-vasp/scripts/plot_band_structure.py` to
  `skills/simflow-analysis-visualization/scripts/plot_band_structure.py`.
  EIGENVAL parsing still uses the shared `VASPParser`; KPOINTS line-mode label
  extraction remains inline format glue. VASP skill now ships only
  `generate_*_inputs` / `validate_*` / `orchestrate_*` / `troubleshoot_*`.
- Updated `skills/simflow-vasp/SKILL.md` to drop the plotting reference and
  point to the analysis_visualization stage.

### Boundary rule + tests
- `skills/README.md` now documents the domain-skill script allowlist: domain
  skills ship `inspect_*` / `validate_*` / `generate_*_inputs` / `parse_*_outputs`
  / `orchestrate_*` / `troubleshoot_*` / `prepare_*_handoff` / `build_*_manifest`
  only; `analyze_*` / `plot_*` / `audit_figure_*` belong to
  `simflow-analysis-visualization`.
- Tests added: `tests/skills/test_parse_lammps_outputs.py`,
  `tests/skills/test_plot_band_structure.py`; `test_analyze_md_trajectory.py`
  expanded to cover the migrated/ strengthened logic.

## v0.9.0 (2026-07-25) — Audit Remediation Phases 1-5

Phase 1-4 audit remediation across blocking fixes, state automation,
anti-bypass, MCP engagement, artifact lineage, and failure recovery.
issues identified by deep audit of the PEE_NEP and Li-O-B-Si projects
(91 session transcripts + state files + code verification).

### P0.1 — init_workflow idempotent by default
- `init_workflow` no longer overwrites existing `.simflow/state/` files
- New `force=True` parameter backs up to `.simflow/backups/<timestamp>/`
- `workflow_id` and `created_at` preserved across force re-init
- MCP `init_workflow` tool exposes `force` boolean (default false)
- Fixes: `init_workflow` clobbering custom `gates.json` (07/19T19-55-26)

### P0.2 — HPC SSH workstation + LocalConnector signature
- `LocalConnector.dry_run()` now accepts `(script_path, manifest_path, base_dir)`
  matching `SlurmConnector` signature (was taking 2 args, got 4)
- HPC auto-detection: SLURM > SSH workstation > Local (was hardcoded to SLURM)
- `SIMFLOW_SSH_HOST` env var triggers SSHConnector for workstation mode
- `SIMFLOW_SSH_WORKSTATION_MODE=1` explicitly enables nohup bash path
- Unknown scheduler strings now fall back to LocalConnector (was None)
- Fixes: LBS 07/22 `LocalConnector.dry_run() takes 2 positional arguments`

### P0.3 — Literature search defaults to OpenAlex
- New `OpenAlexConnector` (free, no API key required, real scholarly data)
- Auto-detection: S2_API_KEY → SemanticScholar; default → OpenAlex (was Mock)
- Mock connector results now tagged `status='mock_unverified'`,
  `usable_as_evidence=False`
- Tool descriptions updated (removed "mock/dry-run fallback by default")
- Fixes: 06/26T16-17-32 user opt-out "connector 返回 mock/无关结果"

### P0.4 — record_computation_evidence without proposal artifacts
- `_allows_direct_contract` now checks `workflow.json` entry_point/current_stage
  (was only checking empty `metadata.json`)
- Projects with `entry_point=computation` can record evidence without
  proposal.md/parameter_table.csv/research_questions.json
- `_build_direct_entry_contract` prefers `workflow.json` workflow_type
- MCP tool catches `FileNotFoundError` and returns error dict
- Fixes: 3 independent sessions with `Missing proposal artifacts` error

### P0.5 — project_root case normalization
- `resolve_project_root` normalizes path casing via `os.path.realpath()`
- On WSL case-insensitive FS, lowercase paths normalized to disk's real casing
- Issues `UserWarning` when casing is corrected
- Fixes: Li-O-B-Si 28 lowercase path fields in artifacts.json/lineage.json

### P0.6 — register_artifact accepts directory paths
- New `_compute_directory_tree_hash()` walks directory, sorts files, and
  computes a deterministic tree hash
- Directory artifacts get metadata: `is_directory`, `file_count`,
  `total_size_bytes`, `tree_hash`
- Empty directories produce valid hash (not None)
- Fixes: `[Errno 21] Is a directory` in 4 sessions (06/23, 06/24, 06/26)

### P0.7 — Skill-MCP hard-binding via session-level engagement contract
- New `runtime/simflow_core/engagement.py` module
- State-write MCP tools blocked unless `read_state` called in same session
  (30-min timeout, configurable via `SIMFLOW_SESSION_TIMEOUT_MIN`)
- File-backed engagement log: `.simflow/state/mcp_engagement_log.jsonl`
- Prerequisite matrix: exempt (read-only) vs protected (state-write) tools
- Violation returns error code `skill_engagement_contract_violation`
- Integrated into `simflow_state`, `artifact_store`, `checkpoint_store` servers
- Fixes: Batch 4 cargo-cult pattern (243 skill loads, 0 MCP calls)

### Test Coverage
- 48 new tests across 7 test files
- 2 existing tests updated for new mock-fallback behavior
- 2 existing tests updated for engagement contract (added read_state calls)
- Full suite: 823 passed, 7 skipped, 0 failed

### Phase 2 — P1 State Automation + P2 Anti-Bypass

#### P1.1+P1.5 — touch_workflow auto-refresh
- New `touch_workflow()` helper refreshes workflow.json.updated_at,
  summary.json.updated_at, and regenerates status_summary.md with live
  counts (artifacts, checkpoints, gates, jobs) and stage statuses
- Integrated into `update_stage()`, `create_checkpoint()`, `register_artifact()`
- Fixes: S6->S14 cross-session amnesia (summary.json 4 days stale)

#### P1.2 — Checkpoint auto-upsert stage
- `create_checkpoint` auto-creates canonical stage records in stages.json
  if they don't exist yet (e.g., computation stage referenced but never
  declared via update_stage)
- Fixes: PEE_NEP computation stage missing from stages.json despite 3
  checkpoints, 4 gates, 2 jobs referencing it

#### P1.3 — Snapshot completeness enforcement
- `create_checkpoint` rejects empty or incomplete state_snapshot for
  non-failure checkpoints (requires workflow.json + stages.json)
- Failure checkpoints may be diagnostic-only when canonical recovery state is
  unavailable; diagnostic-only checkpoints cannot be restored
- Fixes: PEE_NEP ckpt_022-024 had no state_snapshot (unrecoverable)

#### P1.4 — Stage_id validation
- Rejects non-canonical undeclared stage_ids with clear error message
- Canonical stages always accepted; custom stages must be declared via
  `update_stage()` first
- Failure checkpoints exempt (with UserWarning)
- Fixes: PEE_NEP 7/24 checkpoints with ad-hoc stage_ids

#### P2.1 — orphan_compute_scanner MCP tool
- Scans project_root for compute directories not in jobs.json/artifacts.json
- Detects VASP (OUTCAR), CP2K, GPUMD/NEP (nep.in+train.xyz), SLURM
  (slurm-*.out), LAMMPS markers
- Flags risky directory names (NoGate, Relaxed, Bypass, SkipGate)
- Writes .simflow/reports/orphan_compute_audit.md

#### P2.2 — Risky directory detection
- orphan_compute_scanner flags directories with NoGate/Relaxed/Bypass/
  SkipGate patterns
- Detects LBS NoHighTGate bypass directory

#### P2.3 — record_user_override MCP tool
- Records user-approved gate bypasses in gates.json with
  decision='user_override'
- Required fields: gate_id, approver_context, risk_note
- Appends to existing gates (does not overwrite)
- Rejects duplicate gate_id

#### P2.4 — record_submit_job gate enforcement
- `record_submit_job` now requires gate_decision_id from approved gate
- Verifies gate exists in gates.json
- User overrides allowed via user_override=True + override_gate_id
- Override gate must have decision='user_override' in gates.json

#### P2.5 — Approval reviewer discipline contract
- New docs/approval_reviewer_simflow_contract.md specification
- Defines 6 signals reviewers should check (cargo-cult, state-write
  without read, unregistered compute, risky dirs, stale state, missing
  stages)
- Includes reviewer rationale template

### Phase 2 Test Coverage
- 36 new tests across 5 test files
- 3 existing tests updated for stage_id canonical naming
- Full suite: 859 passed, 7 skipped, 0 failed

### Phase 3 — P3 Skill Usage Rate + P7 New Layer

#### P3.1 — Auto-read_state middleware
- When a read-only tool (workflow_status, stage_readiness, etc.) is called
  and no prior engagement exists, the middleware auto-records a read_state
  call in the engagement log
- Satisfies prerequisites for subsequent state-write tools automatically
- Reduces friction: agents that check status get their read_state met

#### P3.2 — session_handoff MCP tool
- New simflow_state/session_handoff tool generates compact handoff report
- Report includes: workflow state, latest checkpoint, counts, stage statuses,
  engagement status, warnings (stale state, empty gates, missing stages),
  and suggested next steps
- Written to .simflow/reports/session_handoff_<timestamp>.md

#### P3.3 — Auto-verification on stage completion
- update_stage(completed) auto-creates a 'pending' verification
  record in verification.json
- Ensures verification.json is never empty when stages are completed
- Verification includes checkpoint_id reference when available

#### P3.4+P7.1+P7.2 — Task-shape-aware router + skill-contract schema
- skill-contract.schema.json: new required_mcp_tools, minimum_mcp_engagement,
  task_shapes fields
- router_contract.json: task_shape_engagement_policy with 4 task shape
  patterns (multi_stage_research, single_stage_compute, analysis_only,
  literature_review), each with minimum engagement levels
- simflow/SKILL.md: Required MCP Engagement section + Quick Start for
  Re-entering a Project section

### Phase 3 Test Coverage
- 21 new tests across 3 test files
- 1 existing test updated for verification timestamp accommodation
- Full suite: 880 passed, 7 skipped, 0 failed

### Phase 4 — P4 Artifact Lineage + P5 Failure Recovery + P6 Integration

#### P4.1 — Transactional artifact registration
- Artifact registration now updates `artifacts.json`, `lineage.json`, and the
  producing stage's `outputs` in one rollback-protected transaction
- Every artifact records its `workflow_id`; stage output IDs are deduplicated
- Optional helper-run recording preserves its `record_only` contract and does
  not mutate stage state

#### P4.2 — Directory and evidence-graph provenance
- Directory tree hashes now bind relative path, file size, and content digest
  using `sha256-path-size-content-v1`
- Evidence graph edges retain link IDs, parameters, and timestamps; nodes expose
  software, parameters, and creation time
- Unknown artifact queries return `not_found_artifact_ids`
- Artifact Store read tools now require explicit `project_root`

#### P5.1 — Centralized stage failure lifecycle
- New `record_stage_failure()` core operation and
  `simflow_state/record_stage_failure` MCP tool
- Runner errors and exceptions automatically write sanitized logs and structured
  error reports, register both as artifacts, mark workflow/stage summaries
  failed, create fail verification evidence, and create a failure checkpoint
- Failure results identify the latest successful checkpoint as the recovery
  target; failure and successful checkpoint references are stored separately
- Retrying a stage clears stale failure messages and report references

#### P5.2 — Safe checkpoint recovery semantics
- Checkpoints expose `recoverable` and optional structured `failure_context`
- Diagnostic-only checkpoints are rejected by restore
- Readiness only counts successful checkpoints as completed boundary evidence
- `checkpoint_store/restore` now participates in MCP engagement enforcement

#### P6.1 — Public documentation and integration coverage
- Added `docs/mcp-tool-reference.md` with actual wire-level tool names,
  engagement rules, state effects, and recovery behavior
- Updated state/re-entry, OpenAlex fallback, credential, and MCP design docs
- Added cross-server MCP lifecycle coverage from status/read engagement through
  directory artifact registration, checkpoint, verification, and handoff

### Phase 4 Test Coverage
- 8 net new tests, including centralized failure and cross-server MCP lifecycle
- Schema runtime fixtures validate new artifact, stage, checkpoint, lineage, and
  verification fields
- Full suite: 888 passed, 7 skipped, 0 failed

### Phase 5 — P7.3 Host Adaptation + State Repair

#### P7.3 — MCP clientInfo host adaptation
- New shared `host_adaptation.py` detects Codex, Claude Code, or generic MCP
  clients from the standard initialize handshake
- `simflow_state` emits host-specific invocation guidance while preserving
  identical project-root, engagement, artifact, checkpoint, and safety rules
- No skill-load hook, transcript access, cwd inference, or host-specific
  workflow implementation is required
- Codex and Claude plugin validators now verify their matching initialization
  guidance

#### repair_state audit/apply
- New `simflow_state/repair_state` tool defaults to strictly read-only audit
- Apply mode requires prior `read_state`, rejects thresholds at or below 0.8,
  re-audits immediately, and creates a full `.simflow` backup
- Safe repairs include workflow IDs, lineage-node projections, canonical stage
  declarations and outputs, live path casing, known checkpoint statuses and
  recoverability, workflow activity state, and summary projection
- Scientific completion, unknown lineage parents, historical workflow IDs,
  checkpoint snapshots, checksums, jobs, and gates remain unchanged
- Backup uses byte-copy semantics compatible with DrvFS and cleans incomplete
  backups after failure

#### Authorized project repairs
- `/mnt/d/PEE_NEP`: applied 444 high-confidence repairs across two backed-up
  passes; retained 267
  provenance/custom-stage findings as audit-only; 200 artifacts and lineage
  nodes now align with workflow and stage outputs
- `/mnt/d/Li-O-B-Si`: re-audited immediately before apply and repaired the
  then-current 23 artifacts and 6 checkpoints, including path-case correction
- Both projects preserve checkpoint snapshots byte-semantically and produce
  repair reports plus complete pre-repair backups

### Phase 5 Test Coverage
- 19 net new tests for repair planning/apply, rollback and conflict handling,
  production stdio engagement, host detection, initialization guidance, and
  router policy
- Full suite: 907 passed, 7 skipped, 0 failed

## Unreleased (previous)

### Fixed
- Bump the public plugin version to `0.8.13` so Claude Code rebuilds the installed plugin cache and exposes the packaged `simflow-gpumd` and `simflow-mlp` skills after marketplace updates.
- Add a release guard that blocks marketplace publication when packaged skills change without a plugin version bump.

### Added
- Add a Claude Code adapter as a parallel distribution layer with `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `.claude.mcp.json`, Claude marketplace wrapper build/publish scripts, validation, and quickstart/release documentation.

### Unchanged
- Codex marketplace packaging, `.codex-plugin/plugin.json`, Codex install/update scripts, MCP startup wrapper, and VASP/CP2K/Writing workflow business logic are unchanged.

## v0.8.3 (2026-05-05)

### Fixed
- Fix MCP Python package import collision by making the repository `mcp/` tree an explicit package and preserving plugin-root import precedence during MCP startup.
- Add regression coverage for third-party `mcp` packages appearing earlier in `PYTHONPATH`.
- Print full MCP startup stderr from plugin validation to make import failures easier to diagnose.

## v0.8.2 (2026-05-05)

### Changed
- SimFlow now defaults to using the existing repository root as both the Codex marketplace root and plugin root.
- Added repository-root `.agents/plugins/marketplace.json` with the `simflow` entry pointing to `./`.
- Updated Codex quickstart documentation so normal installation uses `codex plugin marketplace add ~/simflow`; `build:marketplace` is retained only as an optional clean wrapper publishing path.
- Updated plugin validation to check the repository-root marketplace by default and validate generated wrappers only when `SIMFLOW_MARKETPLACE_ROOT` is set.

## v0.8.0 (2026-05-05)

### Added
- **VASP Orchestration Layer** — `simflow-vasp` now routes common VASP tasks instead of acting as a thin task note
  - Common-task coverage for relax, static SCF, DOS, band structure, AIMD, NEB basic, and surface/adsorption/defect input checks
  - New runtime adapters for VASPKIT detection/planning, py4vasp-first post-processing, official VASP Wiki/py4vasp lookup, task validation, and VASP workflow report generation
  - New VASP orchestration scripts for report generation and troubleshooting summaries with official-source links
  - Common VASP task templates for relax, static, DOS, band, AIMD, and NEB basic
  - New tests covering task routing, fallback behavior, metadata-only POTCAR handling, safety gate behavior, and artifact/checkpoint writes

### Changed
- `skills/simflow-vasp/SKILL.md` now explicitly defines the skill as a tool orchestration layer rather than a VASP/VASPKIT/py4vasp replacement
- `runtime/scripts/parse_vasp.py` now prefers `py4vasp` when `vaspout.h5` is present and falls back to SimFlow parsers otherwise
- `skills/simflow-vasp/scripts/generate_vasp_inputs.py` now emits POTCAR metadata/instructions only and avoids generating or distributing POTCAR content

## v0.7.0 (2026-05-04)

### Added
- **CP2K Module** — Complete CP2K input generation and output parsing
  - `runtime/lib/cp2k_input.py`: AIMD NVT and DFT single-point input builders, multi-element KIND blocks (H–Ca), EXTXYZ trajectory format (CP2K 2026), CIF→XYZ conversion
  - `runtime/lib/parsers/cp2k_parser.py`: .log parser (CP2K v2025.1+), .ener parser, trajectory parser (XYZ + EXTXYZ)
  - 46 CP2K-specific tests, 4 test fixtures
  - CP2K skill definition (`skills/simflow-cp2k/`)
  - CP2K templates (`templates/cp2k/`)
  - H2O AIMD→DFT closed-loop example (`examples/h2o/`)
- **Si Band Structure Example** — VASP relax→SCF→bands workflow (`examples/si_band_structure/`)
- **Installation Guide** — `docs/installation.md` covering dependencies, installation, HPC setup, troubleshooting

### Changed
- All HPC configuration now uses environment variables instead of hardcoded paths
- `.gitignore` expanded to exclude generated outputs, large binaries, and local settings

## v0.6.0 (2026-05-03)

### Added
- VASP enhancements, SLURM connector, file handoff

## v0.5.0 (2026-05-03)

### Added
- **Phase 16: E2E Integration Tests** — Full pipeline tests for DFT, AIMD, MD workflows; MCP server integration tests; checkpoint recovery tests (6 new test files)
- **Phase 19: Template Rendering Engine** — Jinja2-compatible renderer (`runtime/lib/template.py`) supporting `{{ var | default() }}`, `{% if/elif/else %}`, `{% for %}` without Jinja2 dependency; 16 tests covering VASP, QE, LAMMPS, Gaussian, SLURM templates
- **Phase 20: Verification Gate Engine** — Gate execution module (`runtime/lib/gates.py`) loading 9 gate definitions, evaluating conditions, recording decisions; wired into `transition_stage.py` via `--gate` option; 13 tests
- **Phase 21: Release Preparation** — `pyproject.toml` with optional deps (pymatgen, MDAnalysis, ase); GitHub Actions CI for Python 3.10-3.13; Node.js validation
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

### Changed
- **Phase 17: Connector Robustness** — All HTTP connectors now use retry_with_backoff + TTLCache; structured error handling replaces bare `except Exception`; ArXiv uses HTTPS
- **Phase 17: Shared Transport** — MCP servers (literature, structure, hpc) now use `mcp/shared/transport.py` instead of duplicated stdin loops
- **Phase 18: Structured Output** — runtime scripts (init_simflow_state, transition_stage, dry_run, validate_outputs) emit structured JSON with actionable suggestions
- **Phase 18: Version Alignment** — plugin.json, package.json, User-Agent all at v0.5.0

### Fixed
- BCC structure building: corrected species count from 1 to 2 for 2-atom BCC cell
- validate_structure: fixed PeriodicNeighbor `in` operator TypeError by using getattr
- MCP server module isolation: tests use importlib.util to avoid name collisions
- Template engine: boolean literal "True" now evaluates correctly in conditions

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
