# GPUMD NEP Evidence

Use `simflow-mlp` for general dataset coverage, validation design,
active-learning readiness, and production MLP-MD readiness. This reference
owns NEP-specific files and training-mode semantics.

## Training modes

### Foundation-model fine-tuning

GPUMD/NEP v5.5 documents foundation-model fine-tuning with:

`fine_tune <nep_model_file> <nep_restart_file>`

This capability is **officially-supported**. The keyword syntax, compatible
model/restart pair, architecture constraints, and bundled NEP89 examples are a
**version-sensitive implementation**. Record both parent files, their hashes,
the target dataset, the NEP version, and the resulting model lineage.

### Ordinary checkpoint/restart

An existing `nep.restart` represents ordinary checkpoint/restart of a training
lineage. Record the parent checkpoint, compatible `nep.in`, continued metrics,
stop reason, and resulting `nep.txt`. Ordinary restart is not the same as
foundation-model fine-tuning.

### Community two-step training

Community two-step training uses ordinary restart while changing selected
training policy such as loss weights, batching, or regularization. It is an
optional, NEP-specific, community-derived strategy with version-sensitive
implementation details. It is not a general MLP requirement and should not be
inferred merely because `nep.restart` exists.

For NEP-related work, record:

- Dataset sources, splits, element coverage, structure counts when known, and parent DFT label provenance.
- Training configuration file, model artifact, loss/metric files, selected training command as user-provided text, version/environment notes, and hashes.
- Training mode, optimizer/evolution strategy when documented, loss policy,
  restart or fine-tuning parent files, checkpoint lineage, and stopping
  conditions.
- Validation evidence such as held-out metrics, property-level checks, short MD smoke tests, and anomaly/extrapolation criteria.
- Active-learning round identifiers and links between candidate selection, labeling, training, validation, and backfill decisions.

Do not treat a `nep.txt` file or `loss.out` trend alone as production readiness evidence.

Load `gpumd_nep_community_methodology.md` for cleaned community claims. Do not
copy fixed community parameter values into this evidence contract.
