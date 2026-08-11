# User Project Layout Guidance

SimFlow respects the user's existing project layout. Directory structure is
project organization, not runtime state, and it must not determine Skill
selection, block scientific work, or trigger an automatic migration.

## Hard Boundaries

Only three directory rules are enforced by runtime:

1. `.simflow/` has one canonical root at the explicit `project_root`.
2. Credentials and restricted file contents must not enter `.simflow/`, Git,
   logs, checkpoints, or distribution packages.
3. SimFlow writes stay inside the user-authorized project path.

Nested historical `.simflow/` directories are reported as migration risks but
are not moved or deleted automatically.

## Recommended New-Project Template

For a new project with no established organization, the following phase names
are a useful template:

```text
phase1_literature_review/
phase2_proposal/
phase3_modeling/
phase4_computation/
phase5_analysis_visualization/
phase6_writing/
```

Create only the phases that are useful. Fixed phase numbers preserve shared
vocabulary, but phases are not mandatory workflow transitions. A project may
also use descriptive directories, an existing lab convention, or an external
workflow system.

Inside a phase, `stageN_<descriptor>/` can be useful for ordered activities,
but it is optional. Existing bare `stage*` directories, method names, material
names, or campaign folders remain valid. SimFlow must not rename them merely to
match the template.

Shared directories such as `scripts/`, `reference/`, `config/`, `tests/`,
`docs/`, `archives/`, and `scratch/` are recommendations, not a root allowlist.
Do not pre-create empty trees or require fixed README, manifest, status, or
protocol filenames before work can proceed.

## Existing-Layout-First Resolution

Before suggesting a location, inspect:

- current directories and naming conventions;
- script-relative paths and scheduler working directories;
- existing `analysis/`, `results/`, README, and workflow indexes;
- the actual set of inputs consumed by the new work.

Prefer an existing equivalent directory name. Do not move, rename, duplicate,
or replace existing files unless the user explicitly approves a migration.
Layout diagnostics are advisory reports only.

## Analysis Placement

Analysis placement balances physical provenance with discoverability. Determine
the inputs first, then choose their nearest meaningful scientific scope.

1. **One calculation unit:** use that unit's existing `analysis/`, `results/`,
   or equivalent directory.
2. **Multiple runs or cases in one stage:** use one stage-level analysis entry;
   do not create a user-facing `analysis/` under every run.
3. **Multiple stages in one phase:** use a phase-level analysis entry such as
   `phase4_computation/analysis/<topic>/`.
4. **Cross-phase but not project-level work:** use the nearest meaningful common
   parent. Do not promote it to phase 5 automatically.
5. **Project-level synthesis:** only analysis supporting project-wide or paper
   conclusions belongs physically in `phase5_analysis_visualization/`.

Technical containers such as `runs/`, `cases/`, `outputs/`, `raw/`, and `data/`
are not automatically scientific scopes.

## Shallow Analysis Entry

One authoritative location does not require the user to search deep trees.
For analysis that SimFlow creates or takes responsibility for maintaining:

- place a `README.md` or existing equivalent index at the analysis scope root;
- link the purpose, consumed inputs, current conclusion, main report, key
  figures, and key tables directly from that entry;
- keep the main report at the root or one level below it;
- place per-case tables, caches, arrays, and debug output under `details/` or
  `work/`;
- keep reusable scripts under the project's existing analysis-script location;
- use relative Markdown links for project navigation;
- never copy results or add cross-platform-fragile symlinks to create a second
  apparent source of truth.

When a phase-5 directory exists, its README may link local stage/phase analyses
without moving them. For projects without a suitable root index, the fallback
navigation file is `.simflow/reports/analysis_index.md`.

## REE Force-Field Example

For a stage containing both `analysis/stage0_results/report.md` and
`tests_2ns/analysis/report.md`, the immediate problem is fragmented navigation,
not the existence of local analysis.

The non-destructive recommendation is:

```text
stage1_force_field_validation/
├── README.md
├── analysis/
│   ├── README.md        # links stage0, 2 ns, and future comparisons
│   ├── figures/
│   ├── tables/
│   └── details/
├── runs/
└── tests_2ns/           # existing inputs and outputs remain in place
```

The stage analysis README identifies the recommended main result. A phase-5
README may link it, while phase 5 contains only genuine project-level synthesis.
Moving existing reports is a separate, user-approved migration after checking
all relative references.

## Runtime Helper

`runtime.simflow_core.layout` provides read-only advisory functions:

- `inspect_layout(project_root)` describes the existing shape and migration
  signals without writing;
- `recommend_analysis_location(project_root, input_paths, ...)` returns one
  authoritative location plus shallow navigation targets.

The helper never creates directories, changes state, copies results, or blocks
work.
