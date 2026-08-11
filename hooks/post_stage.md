# Post-Task Advisory Hook

## Trigger

After a meaningful research task or deliverable.

## Actions

1. Verify the requested scientific result or file.
2. State uncertainty, incomplete evidence, and execution status accurately.
3. Append at most one logical runtime record when durable provenance is useful.
4. Include key file/hash references and parent record IDs in that record.
5. Create a checkpoint only when restart or recovery references exist.

Do not update legacy stage/artifact/lineage registries or create a checkpoint
merely because a task ended.
