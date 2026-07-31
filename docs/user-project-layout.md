# User Project Layout Convention

This document defines the directory naming convention for SimFlow user
projects (the `project_root` where `.simflow/` lives). It is a research-stage
contract: it tells the host agent where to place new artifacts so that the
on-disk tree stays 1:1 with `.simflow/state/stages.json` and so that humans
can find things later without an index.

It does not change SimFlow's runtime state schema, MCP tool signatures, or
the plugin repository's own structure (see `docs/target-repo-structure.md`
for the plugin layout). Existing projects are not required to migrate; this
is the contract for new work and for any future reorganization.

## Motivation

Two real projects were inspected and both show the same failure mode: the
project root accumulates dozens of flat sibling directories that do not map
to the SimFlow canonical stages, a single canonical stage collapses into
many same-prefixed siblings doing different things, and backups, scripts,
logs, and stray files leak into the production namespace. This document
codifies the fixes so future projects avoid those traps.

Reference counter-examples (names cited for illustration only; the projects
themselves are not modified):

- `PEE_NEP/` — 95 root entries, 30+ top-level `stage0_*`..`stage18_*`
  siblings, 10 `stage3_*` siblings doing different things, 12
  `vasp_label_jobs_*` siblings, stray `.simflow/` roots inside two stage
  directories, `POTCAR.test` and `*.tar.gz` at the root.
- `Li-O-B-Si/` — 30 root directories with no stage numbering at all,
  `NEP_Training_*` overloaded for both dataset-prep and actual runs, bare
  integers `2050/2100/2118/2120` encoding iteration counts that look like
  temperatures, 527 MB `DFT_DataSets.zip` at the root.

## Two-Layer Naming

### Top level — `phaseN_<canonical_stage_name>/`

The top level of a user project uses exactly the six canonical SimFlow
stages, each prefixed with a fixed phase number:

```text
phase1_literature_review/
phase2_proposal/
phase3_modeling/
phase4_computation/
phase5_analysis_visualization/
phase6_writing/
```

Rules:

1. **Fixed numbering, no renumbering.** `phase1` is always
   `literature_review`, `phase4` is always `computation`, and so on. If a
   project does not perform a stage, that directory is simply absent; the
   remaining phases keep their canonical numbers. A computation-only
   project has `phase4_computation/` and `phase6_writing/` — it does not
   renumber them to `phase1_*` / `phase2_*`.
2. **Only create a phase directory when the work is actually being done.**
   Do not pre-create empty phase skeletons.
3. **No bare `stageN_*` at the top level.** The `stageN_*` form is the
   second-layer name and must live inside a `phaseN_*` directory. A
   top-level `stage3_aimd/` is a violation; it must be
   `phase4_computation/stage3_aimd/`.
4. **No descriptive-only top-level experiment directories.** A top-level
   `NEP_Training_LBS_Transport_DFT_2120/` is a violation; it must live
   under `phase4_computation/stageN_*/`.

### Second level — `stageN_<snake_case_descriptor>/`

Inside a phase, sub-activities use a locally numbered stage name:

```text
phase4_computation/
├── stage1_initial_models/
├── stage2_vasp_relax/
├── stage3_aimd/
│   ├── 300K/
│   ├── 500K/
│   ├── constrained/
│   └── analysis/
├── stage4_dft_labels/
│   ├── round01_nepv3_neptrainkit/
│   └── round02_nepv4_active/
└── stage5_mlp_training/
    └── nepv5/
        ├── dataset_prep/
        ├── run_step1_from_scratch/
        └── run_step2_finetune/
```

Rules:

1. **Numbering is local to the parent phase.** `phase3_modeling/stage1_*`
   and `phase4_computation/stage1_*` are independent number spaces.
2. **One `stageN_*` equals one logical sub-activity.** Do not split a
   single activity into many same-prefixed siblings. The `PEE_NEP`
   pattern of `stage3_aimd`, `stage3_500K`, `stage3_700K`,
   `stage3_constrained`, `stage3_npt_i`, `stage3_cutoff_convergence`,
   `stage3_aimd_analysis` all sitting at the same level is a violation:
   temperature and method variants belong as subdirectories of one
   `stage3_aimd/`.
3. **Stage numbers are contiguous.** Do not leave gaps. If a stage is
   abandoned, renumber the later siblings or collapse the abandoned one
   into a sibling subdirectory.
4. **Prep and run must be separate directories.** If a stage produces both
   a dataset and a run on that dataset, the same `stageN_*` directory
   may hold a `dataset_prep/` subdirectory and `run_step1/`,
   `run_step2/` subdirectories. The `Li-O-B-Si` pattern of
   `NEP_Training_LBS_Transport_DFT_2050/` (prep) sitting next to
   `NEP_Training_LBS_Transport_DFT_2050_Training/` (run) with the same
   prefix overloaded for both is a violation.
5. **Iteration uses `vN_<desc>_<YYYYMMDD>/`, not bare integers.** The
   `Li-O-B-Si` pattern of `2050`, `2100`, `2118`, `2120` as directory
   names is a violation: those look like temperatures or years and the
   `2118` one is internally rounded to 1920. Use
   `v1_2050frames_20260722/`, `v2_2120frames_20260723/`.
6. **NEP / MLP version names are lowercase with underscores.** Use
   `nepv1`, `nepv2`, `nepv3`, `nepv3p5`, `nepv3p6_lafix`, `nepv4`,
   `nepv5`. Do not mix `NEPv1`, `nep89_reeohcl`, `NEPv3p6_LaFix`,
   `nep89_20250409` capitalizations in the same tree.

## Analysis Placement

Analysis output placement depends on its scope:

- **Single-stage analysis** — nest it inside the source stage as
  `analysis/`. The `PEE_NEP` pattern of `stage3_aimd_analysis/` sitting
  as a sibling next to `stage3_aimd/`, while
  `stage3_aimd_400k_from_sm_final/analysis/` is nested, is a violation.
  Pick the nested form; do not use the `_analysis` suffix to make a
  sibling.
- **Cross-stage analysis** — place it under
  `phase5_analysis_visualization/stageN_<topic>/`. For example, a
  comparison of NEPv2 vs NEPv3 model similarity belongs at
  `phase5_analysis_visualization/stage1_nep_version_similarity/`, not at
  the project root as `nepv2_nepv3_similarity_pca_analysis/`.

## Stage Run-Directory Contract

Every `stageN_*` directory that runs a calculation should contain at
minimum:

```text
stageN_xxx/
├── README.md                  # what this stage does
├── protocol.json              # parameters
├── input_manifest.tsv         # input listing
├── output_check_summary.tsv   # output verification
├── run_status.tsv             # per-case run status
├── run_serial.sh              # driver script (generic ones live in scripts/submit/)
└── static_validation.json     # static validation
```

Task-specific scripts stay with the calculation. Reusable submit scripts
belong under `scripts/submit/` (see `docs/user_guide.md`).

## Cross-Stage Shared Directories

The following live at the project root and are shared across phases. They
are not numbered:

```text
scripts/        # cross-stage shared scripts; submit/ is the reusable submit-script library
reference/      # reference papers, author baseline models, external structures
config/         # cross-stage shared input templates (vasp/, cp2k/, packmol/, ...)
templates/      # cross-stage shared structure templates
tests/          # the single test location; do not duplicate test_*.py under scripts/
docs/           # project documentation (README, workflow.md, conventions)
archives/       # all .zip / .tar.gz / physical backups / quarantined failed experiments
legacy/         # author legacy files preserved for reference
scratch/        # all temp_* / experimental directories consolidated
```

Rules:

1. `scripts/` is the single shared script directory. If a project already
   uses `tools/` for the same purpose, pick one and collapse the other;
   do not maintain both.
2. `tests/` is the single test location. The `PEE_NEP` pattern of 42
   `test_*.py` under `tests/` plus 14 more under `scripts/` is a
   violation.
3. `archives/` holds all backups and tarballs. Timestamped backups use
   `archives/YYYYMMDD_<short_desc>/`. Quarantined failed experiments use
   `archives/quarantined_YYYYMMDD_<desc>/`. The `PEE_NEP` pattern of
   `stage3_npt_i.local_before_remote_sync_20260513_113230/` sitting next
   to the live `stage3_npt_i/` is a violation.

## Root File Allowlist

The project root may contain only:

- `README.md`, `workflow.md`, `.gitignore`
- `.git/`, `.simflow/`
- The six `phaseN_*` directories (only those in active use)
- The nine shared directories listed above

The following are **forbidden** at the project root (real
counter-examples from the inspected projects):

- Pseudopotential / potential files: `POTCAR.test`
- Archives: `*.tar.gz`, `*.zip` (527 MB `DFT_DataSets.zip`)
- Frozen models: `*.pb`, `*.xyz` bulk reference structures
  (`reference-structures-LiLaZrO-PBEsol.xyz` — a 40 MB file belonging to
  a different material system)
- Process state: `train.pid`
- Scripts: `*.py`, `*.sh` (`vasp_convergence_analysis.py`,
  `submit_vasp_label_jobs_slurm.sh`)
- Logs and status: `*.log`, `*.tsv`, `*.stdout`, `*.stderr`,
  `status.tsv`, `driver.*`
- Backups: `*.bak.*`, `workflow.md.bak_*`
- Planning docs that belong in `docs/`:
  `stage3_hpc_submit_plan_*.md`

All of these belong inside the relevant `stageN_*` directory, or under
`scripts/`, `docs/`, `archives/`, or `legacy/` as appropriate.

## Relationship With `.simflow/`

1. **`.simflow/` is the only workflow state root.** It lives at
   `project_root` and nowhere else. A `phaseN_*/stageN_*/.simflow/` or
   any nested `.simflow/` is a violation of `AGENTS.md` State Boundary.
   The `PEE_NEP` pattern of `stage14_*/.simflow/` and
   `stage15_*/.simflow/` is a violation.
2. **`stages.json` should record the on-disk path** of each stage as
   `phaseN_<canonical>/stageN_<descriptor>` so that state and disk stay
   1:1.
3. **`.simflow/artifacts/<stage>/` uses the canonical stage name
   allowlist only:** `literature_review/`, `proposal/`, `modeling/`,
   `computation/`, `analysis_visualization/`, `writing/`, `figures/`,
   `security/`. The duplicated non-canonical names `compute/`,
   `analysis/`, `literature/`, `models/` are forbidden. Both inspected
   projects had these duplicate empty directories.
4. **Real product files stay in their source `stageN_*` directory.**
   `.simflow/artifacts/<stage>/` is for lightweight metadata snapshots
   and deliverables that must be detached from the source tree — not a
   second copy of every output. Reference outputs through
   `artifacts.json` `path` fields.
5. **Gate markers live in `.simflow/state/gates.json`.** Scattered
   `APPROVE_*` files inside `stageN_*` directories are a violation. The
   `PEE_NEP` pattern of `APPROVE_MACE_PRODUCTION` inside `stage14_*`
   and `APPROVE_STAGE17_GPU_EXECUTION` inside `stage17_*` is a
   violation.

## Minimal Project Example

A computation-heavy project that skips literature review and proposal:

```text
my_project/
├── .simflow/
├── .git/
├── phase3_modeling/
│   └── stage1_initial_models/
│       └── La/  Ce/  ...  Lu/
├── phase4_computation/
│   ├── stage1_vasp_relax/
│   ├── stage2_aimd/
│   │   ├── 300K/
│   │   ├── 500K/
│   │   └── analysis/
│   ├── stage3_mlp_training/
│   │   └── nepv5/
│   │       ├── dataset_prep/
│   │       │   └── v1_2050frames_20260722/
│   │       ├── run_step1_from_scratch/
│   │       └── run_step2_finetune/
│   └── stage4_mlp_md_validation/
├── phase5_analysis_visualization/
│   └── stage1_nep_version_similarity/
├── phase6_writing/
├── scripts/
│   └── submit/
├── reference/
├── config/
├── tests/
├── docs/
├── archives/
├── README.md
├── workflow.md
└── .gitignore
```

Note `phase1_literature_review/` and `phase2_proposal/` are absent (work
not performed) and the remaining phases keep their canonical numbers.

## Enforcement

Directory hygiene checks are specified in the `simflow-verify` skill
(`Directory Hygiene Checks` section). The host agent performs them as
text-level checks when verifying a project; SimFlow does not ship a
separate validator binary for this.
