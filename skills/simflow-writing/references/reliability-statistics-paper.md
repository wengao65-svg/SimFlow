# Reliability and Statistics Computational Simulation Paper

Use for papers about uncertainty quantification, sampling adequacy, statistical variance, reproducibility, confidence intervals, active-learning reliability, or error analysis in AIMD/MD/MLP-MD.

## Core Claim

Frame the paper as:

> We establish a criterion/procedure/error model for deciding when simulation-derived quantity X is reliable.

The novelty is the reliability framework, not only another set of simulations.

## Introduction Logic

1. Identify a widely used computed quantity whose uncertainty is often underreported.
2. Explain why short trajectories, limited events, finite cells, or model error make the quantity fragile.
3. State what existing practice misses.
4. Introduce the statistical or uncertainty framework.
5. Explain how it changes interpretation, reporting, or future simulation design.

## Figure Plan

Fig. 1: Problem illustration. Show how identical workflows can produce scattered values due to limited sampling.

Fig. 2: Theory/statistical framework. Define estimator, variance, confidence interval, event count, block averaging, bootstrap, ensemble model uncertainty, or convergence criterion.

Fig. 3: Controlled validation. Test the method on systems where longer trajectories or reference results are available.

Fig. 4: Practical map. Show required trajectory length/event count/cell size as a function of diffusivity, temperature, barrier, or target uncertainty.

Fig. 5: Case studies. Reanalyze representative AIMD/MD/MLP-MD results.

Fig. 6: Reporting protocol. Provide a workflow or checklist for reliable future studies.

## Required Evidence

- Mathematical definition of the estimator and uncertainty.
- Demonstration against repeated trajectories or long reference simulations.
- Clear practical thresholds, not only qualitative warnings.
- Guidance for reporting uncertainty and convergence.
- Discussion of both statistical uncertainty and model/systematic uncertainty when relevant.

## Common Weaknesses

- Treating statistical variance as the only source of error.
- No independent trajectories or block analysis.
- Recommending impractically long simulations without a decision framework.
- Not connecting the framework to quantities readers actually compute.
