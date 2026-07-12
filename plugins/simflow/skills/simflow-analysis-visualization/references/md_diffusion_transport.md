# MD Diffusion And Transport Analysis

Use this reference for diffusion, viscosity, thermal conductivity, VACF, MSD,
Green-Kubo, NEMD, HNEMD, and related time-correlation analyses.

## Required Evidence

- trajectory or transport-output source files, timestep, units, sampling interval, frame/step count, and production window.
- ensemble, temperature/pressure control, system size, force field or MLP model evidence, and restart/continuation semantics.
- raw correlation, MSD, heat-current, stress, or modal data preserved beside scalar summaries.

## Methods

- MSD/diffusion: atom selection, unwrapping/image handling, time-origin strategy, dimensionality, linear fit window, unit conversion, and block or seed uncertainty.
- VACF/spectra: correlation length, windowing/filtering, normalization, integration range, and spectral resolution.
- Viscosity/thermal conductivity: Green-Kubo or nonequilibrium protocol, integration window sensitivity, block size, finite-size caveats, and uncertainty.

## Claim Limits

Do not present short trajectories, single seeds, rare-event sampling, or
window-sensitive integrals as high-confidence transport properties without
explicit uncertainty and sensitivity checks.
