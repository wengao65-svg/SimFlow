# SimFlow Documentation Index

SimFlow documentation follows the current workflow-layer position: SimFlow
records, checks, gates, and hands off computational research work. It is not a
centralized workflow executor and does not decide the science for the host
agent.

## Start Here

- [README](../README.md): product summary, install notes, and current structure.
- [User Guide](user_guide.md): how to think about stages, recipes, evidence,
  and safety gates.
- [Workflow Layer Design](workflow-layer-design.md): canonical stage and recipe
  semantics.
- [Skill Design](skill-design.md): skill-first contracts and domain assistant
  rules.
- [MCP Design](mcp-design.md): recording-tool boundaries and project-root
  requirements.

## Operations And Safety

- [HPC Integration](hpc-integration.md): dry-run-first submit evidence and hash
  requirements.
- [Credentials Policy](credentials-policy.md): credential handling boundaries.
- [Verification Gates](verification-gates.md): gate concepts and review
  discipline.
- [State And Checkpoint](state-and-checkpoint.md): `.simflow/` state and
  recovery.

## Compatibility And Migration

- [Migration Plan](migration.md): legacy workflow/state migration.
- [Target Repo Structure](target-repo-structure.md): current source layout and
  legacy surface notes.
- [Software Skills](software-skills.md): optional engine helper guidance.

## Legacy Recipe Examples

These examples are retained as recipe/helper documentation. They are not
mandatory executor DAGs and do not imply old `simflow-dft`, `simflow-aimd`, or
`simflow-md` CLIs.

- [DFT Legacy Recipe Example](examples/dft_workflow.md)
- [AIMD Legacy Recipe Example](examples/aimd_workflow.md)
- [Classical MD Legacy Recipe Example](examples/md_workflow.md)
