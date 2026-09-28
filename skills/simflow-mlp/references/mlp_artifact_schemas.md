# MLP Evidence Notes

Use a small, user-owned note or table when an MLP project needs a durable
handoff. The note should point to authoritative dataset, label, model, training,
validation, and smoke-MD files in the user's existing layout. Do not create a
second SimFlow registry or require a fixed JSON schema.

For each claim, retain the information needed to judge it: source files and
versions, element and configuration coverage, label method and units, train and
test split, energy/force/stress metrics by relevant subset, known extrapolation,
and any anomaly thresholds. Distinguish a file that was parsed from a model
that passed the scientific validation needed for the proposed use.

A production-readiness review is a scientific judgment. It does not authorize
real local, remote, or HPC execution. The host's permissions and the user's
authorization control the concrete execution action.
