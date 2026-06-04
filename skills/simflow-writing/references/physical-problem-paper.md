# Physical-Problem Computational Simulation Paper

Use for papers whose main contribution is a physical conclusion about a material, interface, phase transition, transport mechanism, reaction, wetting behavior, defect process, or spectroscopy signal.

## Core Claim

Frame the paper as:

> We resolve/explain/predict X by using validated DFT/AIMD/MLP-MD simulations to reveal mechanism Y.

The model is a means, not the main subject. Lead with the scientific question or controversy.

## Introduction Logic

1. Explain why the physical problem matters.
2. State the unresolved experimental or theoretical ambiguity.
3. Explain why direct experiment, DFT, AIMD, or empirical MD cannot settle it alone.
4. Introduce the validated simulation approach.
5. Preview the mechanism and its broader implication.

## Figure Plan

Fig. 1: Problem and simulation setup. Show material/interface/defect/reaction geometry and the unresolved question.

Fig. 2: Validation. Show MLP/DFT/expt agreement sufficient to trust the following physics.

Fig. 3: Main physical observation from trajectories. Show structures, time evolution, phase signatures, transport pathways, or interfacial motifs.

Fig. 4: Mechanism. Use order parameters, free-energy profiles, coordination, RDF, MSD, spectra, charge/spin analysis, or local environments.

Fig. 5: Connection to experiment or prior theory. Explain measured trends, spectra, phase boundaries, contact angle, diffusivity, thermal conductivity, etc.

Fig. 6: Prediction or design rule. Show how composition, temperature, pressure, thickness, defects, or fields tune the mechanism.

## Results Section Order

1. Simulation framework and validation for this material.
2. Direct observation of the debated or hidden behavior.
3. Microscopic mechanism and order parameters.
4. Quantitative comparison with experiments or high-level calculations.
5. Generalization across conditions and predictive implications.

## Required Evidence

- A clearly stated physical question before method details.
- Validation targeted to the property being claimed.
- Multiple independent descriptors supporting the mechanism.
- Sensitivity checks: cell size, trajectory length, temperature, pressure, functional, seeds, or model uncertainty where relevant.
- Avoid presenting a single trajectory snapshot as proof.

## Common Weaknesses

- The paper reads like a model-validation paper even though the claimed novelty is physics.
- The central mechanism is asserted but not isolated by order parameters or controls.
- Experiment comparison is qualitative when quantitative data are available.
- Alternative explanations are not addressed.
