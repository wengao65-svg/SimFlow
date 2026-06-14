# MLP Task Checklists

## Dataset audit

- Identify dataset files and parent artifacts.
- Record structure counts when safely available.
- Check split definitions and label provenance.

## Validation review

- Record metric names, units, split names, and thresholds if provided.
- Separate interpolation metrics from domain-transfer metrics.
- Check property-level validation for the intended use.

## Readiness review

- Require validation, smoke MD, anomaly thresholds, and approval evidence before production MLP-MD.
- Record missing evidence as blocked or degraded, not passed.
