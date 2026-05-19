# Verification Gates

## Overview

Gates are evidence and approval boundaries. They are not a central workflow
executor and they do not decide the scientific path. A gate evaluates recorded
state or artifact evidence and returns `pass` or `block`.

Legacy boolean-only context is not sufficient for high-risk gates such as real
local, remote, or HPC submit.

## Gate Responsibilities

- verify required evidence exists
- report missing or failing evidence
- require explicit approval for risky actions
- preserve gate decisions with stable ids
- block submit when hashes or evidence no longer match

## Example: hpc_submit

The `hpc_submit` gate reads evidence from project `.simflow/` artifacts and
state:

```json
{
  "id": "dry_run_passed",
  "evidence": "compute/dry_run_report.json",
  "path": "$.status",
  "op": "in",
  "value": ["pass", "warning"]
}
```

Real submit requires:

- dry-run report
- input validation report
- resource estimate
- credential scan
- script/input hash evidence
- approval decision id or approval token

Local submit follows the same approval discipline as remote or HPC submit.

## Actions On Failure

When a gate blocks, SimFlow should record why and stop the risky transition.
The host agent may then gather missing evidence, fix inputs, request user
approval, or create a failure checkpoint.

Do not record a blocked or unapproved real execution as completed.

## Policy Layer

Policies complement gates by describing hard boundaries such as:

- dry-run first
- no credential storage
- checkpoint on stage boundary
- approval for external submit
- artifact versioning and lineage

Policies and gates constrain safety and traceability. They do not hard-code the
literature source, modeling tool, simulation software, parser, plotting library,
or report structure.
