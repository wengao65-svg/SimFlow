# VASP Calculation Class: Hybrid, Meta-GGA, and Dispersion-Corrected Work

Use this reference for hybrid functionals, meta-GGA workflows, van der Waals corrections, and dispersion-corrected adsorption/bulk calculations.

## Official sources

- Hybrid functionals tutorial: https://www.vasp.at/tutorials/latest/hybrids/
- Hybrid functionals category: https://www.vasp.at/wiki/Category:Hybrid_functionals
- LHFCALC: https://www.vasp.at/wiki/LHFCALC
- HFSCREEN: https://www.vasp.at/wiki/HFSCREEN
- Band structures using hybrid functionals: https://www.vasp.at/wiki/Band-structure_calculation_using_hybrid_functionals
- Band structures using meta-GGA functionals: https://www.vasp.at/wiki/Band-structure_calculation_using_meta-GGA_functionals
- Nonlocal vdW-DF functionals: https://www.vasp.at/wiki/Nonlocal_vdW-DF_functionals
- DFT-D3: https://www.vasp.at/wiki/DFT-D3
- DFT-D4: https://www.vasp.at/wiki/DFT-D4

## Minimum evidence

- Functional choice and reason: HSE/PBE0/other hybrid, meta-GGA, nonlocal vdW, or empirical dispersion.
- Predecessor DFT calculation and restart strategy.
- Resource estimate and convergence evidence appropriate to the higher-cost method.

## Tags and files to inspect

- `LHFCALC`, `HFSCREEN`, `AEXX`, `ALGO`, `TIME`, `PRECFOCK`, `NKRED*`, `HFRCUT`, `KPOINTS_OPT`.
- Meta-GGA and vdW/dispersion tags relevant to the selected functional.
- `WAVECAR`, `CHGCAR`, `vaspout.h5`, `OUTCAR`, and memory/time records.

## SimFlow guidance

- Treat hybrid/meta/vdW choices as method-level decisions that affect scientific comparison.
- For hybrid band structures, follow the dedicated hybrid band workflow rather than fixed-density DFT assumptions.
- Register functional choice, predecessor, restart files, resource estimate, and convergence evidence as artifacts.
- Real execution normally requires approval due to cost.

## Common risks

- Assuming hybrid calculations can use `ICHARG=11` like DFT band runs.
- Comparing energies across different dispersion or hybrid settings without rationale.
- Missing k-point and exact-exchange convergence.
- Insufficient memory/resource review before real execution.
