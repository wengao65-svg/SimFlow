# Legacy Workflow Inputs

The files in this directory are legacy workflow inputs retained for
compatibility:

- `dft.json`
- `aimd.json`
- `md.json`

They are not the canonical workflow-layer contract and should not be treated as
mandatory executor DAGs. New work should use canonical stages plus recipe/tag
guidance from `workflow/recipes/*.json`.

Runtime migration and compatibility helpers may still read these files to load
old projects, convert workflow metadata into recipes, or preserve historical
test fixtures. Do not delete them unless compatibility support is intentionally
removed in a separate migration plan.
