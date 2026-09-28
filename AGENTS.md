# SimFlow Agent Guidelines

SimFlow is a portable collection of computational-research Skills. The host
agent works with the user; SimFlow does not manage experiments, run workflows,
or maintain a project ledger.

## Scientific work

- Discover the Research Task and Domain Skills relevant to the current request.
  Combine them with the host's tools and other applicable Skills.
- Treat Skills as guidance for scientific choices, validation, interpretation,
  and communication. A Skill does not grant execution permission or certify a
  result.
- Read the user's existing project files and records when continuity matters.
  Respect the current layout. Write a research note where the user asks or an
  existing project convention clearly calls for it.
- Never initialize, migrate, or write `.simflow/` as a side effect of using a
  Skill. Existing `.simflow/` data belongs to the user and remains untouched.

## Execution and evidence

- Inspect inputs, commands, destination, resource needs, and likely cost before
  real compute, scheduler submission, remote write, destructive action, or
  overwrite. Obtain authorization for the concrete action when it is not
  already provided in the conversation; honor the host's permission and sandbox
  rules. If the action materially changes, reassess its authorization.
- A scheduler job ID proves submission only. File presence or parser success
  does not prove convergence or scientific validity. Report actual status and
  uncertainty from the available evidence.
- Preserve user-provided models and validated scientific parameters unless the
  user authorizes a change. Never fabricate references, results, or figures.
- Keep credentials, tokens, keys, and SSH options out of project records and
  generated artifacts. Handle licensed POTCAR content only from a user-owned
  source into an appropriate calculation directory; never include its content
  in responses, packages, commits, or reports.

The optional six-phase directory template is a starting point for new projects,
not a requirement. Place analysis close to the inputs it uses, and retain one
authoritative result location.
