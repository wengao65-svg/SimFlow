# Skills Directory

SimFlow is skill-first, but not every bundled skill has the same role. The
canonical workflow-layer skills define the current research-stage contract:

- `simflow`
- `simflow-literature-review`
- `simflow-proposal`
- `simflow-modeling`
- `simflow-computation`
- `simflow-analysis-visualization`
- `simflow-writing`
- `simflow-safety-gates`

These skills describe SimFlow's current workflow-layer semantics: research
intent, evidence boundaries, artifact tracking, checkpoints, lineage, safety
gates, and handoff discipline. They do not make SimFlow a centralized workflow
executor.

Other `simflow-*` skills are compatibility entries, optional helpers, domain
assistants, or older stage aliases. They may provide useful checklists, scripts,
or task-specific guidance, but they are not the canonical workflow contract.

Engine skills such as `simflow-vasp`, `simflow-cp2k`, `simflow-qe`,
`simflow-lammps`, and `simflow-gaussian` are optional domain assistants. They
can help inspect inputs, suggest checks, troubleshoot common issues, and record
artifacts, but they do not limit what tools, parsers, scripts, plotting
libraries, or scientific paths a host agent may choose.

When adding new skills, keep hard requirements limited to safety and
traceability. Prefer guidance, recommended evidence, and handoff notes over
fixed parser, builder, software, or report-file requirements.
