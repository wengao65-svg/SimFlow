# Method-Type Computational Simulation Paper

Use for papers whose main contribution is a new MLP architecture, training workflow, sampling strategy, active-learning loop, uncertainty method, pretrained/foundation potential, or general-purpose potential.

## Core Claim

Frame the paper as:

> We introduce X, a method/framework/model that enables Y by overcoming Z.

Examples of Z:

- DFT labeling cost is too high for each new system.
- Existing MLPs are accurate only in narrow chemical or configurational domains.
- Local descriptors miss charge, polarization, magnetism, electric-field response, or long-range interactions.
- Static MAE looks good but long MD trajectories are unstable or physically wrong.
- Active-learning datasets are not demonstrably representative.

## Abstract Logic

1. Name the simulation capability the field needs.
2. State why DFT/AIMD, empirical potentials, and existing MLP workflows are insufficient.
3. Introduce the method in one sentence.
4. Quantify accuracy, data efficiency, transferability, stability, or speed.
5. State the new simulations or downstream results enabled by the method.

## Figure Plan

Fig. 1: Method/workflow overview. Show data generation, model/training loop, uncertainty or pretraining/fine-tuning, and MD deployment.

Fig. 2: Dataset and configuration-space coverage. Show elements, phases, temperatures, pressures, compositions, defects, interfaces, or PCA/UMAP/SOAP maps.

Fig. 3: Accuracy benchmark. Report energy, force, stress, and relevant property errors by subset, not only aggregate MAE.

Fig. 4: Data efficiency or transferability. Compare against baseline models/workflows and show fewer DFT labels, better out-of-distribution accuracy, or better fine-tuning.

Fig. 5: MD robustness and physical validation. Show energy conservation, stable NVT/NPT trajectories, RDF/MSD/phonons/diffusion/thermal conductivity/phase behavior versus DFT, experiment, or trusted literature.

Fig. 6: Enabled application. Demonstrate large-scale, long-time, complex-composition, high-temperature/pressure, interface, defect, reaction, or phase-diagram simulation.

## Results Section Order

1. Overview of the framework/model.
2. Construction and coverage of the training dataset.
3. Accuracy on held-out and physically distinct test sets.
4. Transferability, sample efficiency, or uncertainty-guided improvement.
5. MD stability and property validation.
6. Representative applications enabled by the method.

## Required Evidence

- Baseline comparison against established models or workflows.
- Ablation showing why the new ingredient matters.
- Tests separated by physical regime.
- Long MD stability, not only static force error.
- Clear statement of domain of applicability.
- Failure modes or extrapolation limits when known.

## Common Weaknesses

- Claiming universality from a narrow dataset.
- Reporting a single global MAE without subset analysis.
- Ignoring stress/virial when NPT or mechanical properties are used.
- Using MD applications that merely reproduce training conditions.
- Omitting computational cost of DFT labeling and MLP inference.
- Treating pretraining/fine-tuning as novelty without proving sample-efficiency gains.
