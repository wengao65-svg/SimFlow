# Scale-Breakthrough Computational Simulation Paper

Use for papers whose main novelty is that MLP-MD or an accelerated workflow reaches length, time, chemical, or thermodynamic regimes inaccessible to conventional DFT/AIMD.

## Core Claim

Frame the paper as:

> We access regime X with validated near-DFT simulations, revealing phenomenon Y that was hidden at smaller scales or shorter times.

Scale is not enough by itself; explain what new physics appears because of the scale.

## Introduction Logic

1. State the phenomenon that requires large systems, long times, rare events, or realistic conditions.
2. Quantify why AIMD or small-cell DFT cannot access it.
3. Explain why empirical potentials are unreliable for this chemistry.
4. Present the MLP/accelerated approach as the route to the missing regime.
5. State the discovered behavior or predictive capability.

## Figure Plan

Fig. 1: Scale gap and workflow. Show DFT/AIMD regime versus achieved MLP-MD regime.

Fig. 2: Validation at overlapping scales. Demonstrate agreement with DFT/AIMD and experiments where available.

Fig. 3: Large-scale/long-time simulation evidence. Show system size, trajectory length, rare event statistics, domain evolution, or transport pathways.

Fig. 4: Emergent mechanism. Show why the phenomenon cannot be captured in small cells or short trajectories.

Fig. 5: Scaling or condition map. Show dependence on size, time, temperature, pressure, composition, defects, or fields.

Fig. 6: New prediction. Provide phase diagram, kinetic law, design map, or experimentally testable prediction.

## Required Evidence

- Explicit comparison between accessible AIMD scale and achieved MLP-MD scale.
- Convergence with respect to cell size and trajectory length.
- Multiple independent trajectories or rare-event statistics when stochastic events matter.
- Validation in the overlapping DFT/AIMD regime.
- Clear explanation of why scale changes the conclusion.

## Common Weaknesses

- Boasting about atom count or nanoseconds without a new scientific consequence.
- No convergence study showing the chosen scale is sufficient.
- MLP validation only on small static structures, not dynamical states.
- Claims based on a single rare event.
