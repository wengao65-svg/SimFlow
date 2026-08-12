# Logical Records And File References

## Record Granularity

SimFlow records logical events and deliverables, not every file. Typical record
kinds are milestone, run, artifact, analysis, evidence_change, approval,
failure, and note.

Create a record when durable project history benefits from knowing what
happened. Do not create a record for transient logs, caches, duplicate figures,
intermediate parser output, or helper invocation receipts.

## File References

A record may contain one or more references:

```json
{
  "path": "analysis/rdf/report.md",
  "role": "main_report",
  "sha256": "...",
  "size_bytes": 1234,
  "exists": true
}
```

Paths are project-relative and must stay inside `project_root`. Runtime computes
hash and size for existing files. Restricted entries use metadata-only
references and never persist the body or an unsafe path.

For a run directory or multi-file deliverable, prefer a manifest, directory
tree hash, or a few key references instead of one record per file.

## Provenance

Use `parent_ids` to connect logical events:

```json
{
  "kind": "analysis",
  "summary": "Accepted RDF comparison",
  "parent_ids": ["rec_source_run"],
  "artifacts": [
    {"path": "analysis/rdf/report.md", "role": "main_report"},
    {"path": "analysis/rdf/figure.png", "role": "key_figure"}
  ],
  "details": {
    "script": "scripts/analysis/rdf.py",
    "units": "angstrom",
    "normalization": "pair-density normalized"
  }
}
```

This preserves useful lineage without separate artifact, lineage, stage-output,
and version registries.

## Legacy Schemas

`schemas/artifact.json`, `schemas/checkpoint.json`, `schemas/job_record.json`,
and `schemas/state.schema.json` are labeled read-only compatibility schemas for
historical `.simflow/state` data. They do not define the new compact write
model.
