# Agents Directory

The files in this directory are legacy role prompts and optional review
templates. They are retained for compatibility with older SimFlow packaging and
for teams that still want role-oriented review aids.

They are not the canonical SimFlow workflow entry point and they do not define a
centralized workflow executor. Current SimFlow work should enter through skills,
MCP/runtime helpers, and the `.simflow/` state, artifact, checkpoint, lineage,
gate, and handoff records.

Use these files only as optional context when a host agent or reviewer needs a
role-specific checklist. Do not treat them as the source of truth for stage
progression, software choice, parser choice, report structure, or scientific
decisions.
