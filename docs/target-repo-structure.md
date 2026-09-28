# Repository Structure

```text
skills/<name>/
  SKILL.md       scientific guidance and triggers
  references/    detailed methods, loaded when relevant
  scripts/       optional standalone tools
  lib/           code used only by that Skill's scripts
  assets/        fixed templates used only by that Skill
scripts/         package building, validation, and scaffolding
tests/           scientific behavior and distribution checks
docs/            user and developer guidance
```

A Skill is self-contained, so copying its directory into a compatible host
retains its scripts and local resources. The six-phase layout mentioned in
some Skills is an optional user project template, not a runtime requirement.
SimFlow creates no project state directory or experiment registry.
