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
- [MLP-MD Workflow Recipe](mlp-md-workflow.md): machine-learning-potential MD
  stage mapping, evidence roles, and production-readiness gate.
- [Skill Design](skill-design.md): skill-first contracts and domain assistant
  rules.
- [MCP Design](mcp-design.md): recording-tool boundaries and project-root
  requirements.

## Operations And Safety

- [Release Checklist](release-checklist.md): source, wrapper, metadata, and
  install-smoke gates before publishing.
- [Release Smoke Results](release-smoke-results.md): local record template for
  Codex and Claude install-smoke results.
- [Current Limitations](current-limitations.md): supported helpers,
  unsupported placeholders, and release boundaries.
- [HPC Integration](hpc-integration.md): dry-run-first submit evidence and hash
  requirements.
- [Credentials Policy](credentials-policy.md): credential handling boundaries.
- [Verification Gates](verification-gates.md): gate concepts and review
  discipline.
- [State And Checkpoint](state-and-checkpoint.md): `.simflow/` state and
  recovery.

## Development References

- [Target Repo Structure](target-repo-structure.md): current source layout.
- [Software Skills](software-skills.md): optional engine helper guidance.
