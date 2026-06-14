# GPUMD Task Checklists

## Static input inspection

- Identify GPUMD vs NEP training context.
- List present and missing expected files.
- Check referenced relative paths.
- Record command categories and unknown commands.

## Manifest generation

- Include files, hashes, user command string, tool/version facts, environment notes, evidence role, and lineage.
- Mark `actual_tool_used.support_level` as `tracked_only`.
- Mark helper capability as static inspection, manifest generation, selected output parsing, or evidence handoff.

## Selected output parsing

- Keep raw outputs beside summaries.
- Record parser assumptions and skipped files.
- Avoid pass/fail model or transport conclusions unless thresholds and validation context are explicit.
