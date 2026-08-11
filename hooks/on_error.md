# Error Handling Hook

## Trigger

When a scientific helper, transfer, submit, or analysis operation fails.

## Actions

1. Preserve the real failure status and original evidence.
2. Diagnose before changing scientific parameters.
3. Append one failure/run record only when durable project history is useful.
4. Create a compact checkpoint only if restart references, hashes, or a useful
   diagnostic boundary exist.
5. Report the next diagnostic or recovery action to the user.

Do not automatically rerun, rewrite user files, or mark partial output as
completed.
