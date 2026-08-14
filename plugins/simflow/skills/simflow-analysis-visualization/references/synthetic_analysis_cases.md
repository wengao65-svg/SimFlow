# Synthetic Analysis Cases

These fictional, dimensionless cases test reasoning patterns without shipping
real research data. Use them for Skill review or regression tests, not as
scientific benchmarks.

## Statistical Independence

Negative: One trajectory has 10,000 frames and 100 overlapping time origins.
The analysis reports `n = 1,000,000` and a tiny standard error by treating every
atom-frame-origin value as independent.

Positive: The analysis reports one independent trajectory, treats frames and
time origins as correlated subsamples, uses trajectory-level blocks to assess
stability, and limits the claim until independent seeds are available.

## Comparison Consistency

Negative: Model A energy is total energy with its own zero; Model B energy is
per atom after subtracting its final frame. The curves share one axis and the
lower curve is called the better model.

Positive: The comparison reconciles units, per-atom normalization, common
reference state, composition, sampling conditions, and window. If a common
reference cannot be constructed, the curves remain separate and no ranking is
claimed.

## Sensitivity

Negative: A diffusion coefficient is reported from one fit range selected after
viewing the MSD. Moving either endpoint by a reasonable amount changes the
slope ordering, but only the preferred range appears in the result.

Positive: The default fit range and a small set of defensible alternatives are
reported. The ordering is labeled stable, magnitude-sensitive, sign-sensitive,
or unresolved, and the claim strength follows that result.

## Unexpected Result

Negative: A discontinuous temperature spike after restart is immediately
described as a phase transition.

Positive: The analysis checks parser continuity, units, restart timestamps,
thermostat state, run termination, plotting transforms, equilibration, and model
validity before considering a physical transition, then proposes a diagnostic
that could distinguish the hypotheses.

## Figure And Claim

Negative: A smoothed three-seed curve is captioned "Model X eliminates
instability and is universally transferable." The raw seed spread, smoothing
bandwidth, failed cases, and out-of-domain conditions are absent.

Positive: The figure traces to raw seed-level values and recorded smoothing,
supports only lower observed instability under the tested conditions, displays
or states uncertainty and failed cases, and explicitly does not establish
universal transferability or mechanism.
