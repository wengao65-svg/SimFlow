# VASP Calculation Class: GW, RPA/ACFDT, and BSE

Use this reference for quasiparticle GW calculations, RPA/ACFDT total energies, Bethe-Salpeter optical excitations, and related many-body workflows.

## Official sources

- Practical guide to GW calculations: https://www.vasp.at/wiki/Practical_guide_to_GW_calculations
- GW tutorial: https://www.vasp.at/tutorials/latest/gw/
- ACFDT/RPA calculations: https://www.vasp.at/wiki/ACFDT/RPA_calculations
- Bethe-Salpeter-equations calculations: https://www.vasp.at/wiki/Bethe-Salpeter-equations_calculations
- Best practices for Bethe-Salpeter calculations: https://www.vasp.at/wiki/Best_practices_for_Bethe-Salpeter_calculations
- BSE tutorial: https://www.vasp.at/tutorials/latest/bse/
- NBANDS: https://www.vasp.at/wiki/NBANDS

## Minimum evidence

- Clear predecessor chain: ground-state calculation, orbitals/density, empty-band convergence, and any intermediate response files.
- Target quantity: quasiparticle gap, spectral function, RPA energy, optical absorption, exciton analysis, or screening.
- Convergence plan for bands, k mesh, cutoffs, frequency grids, dielectric matrix, and response settings.

## Tags and files to inspect

- `ALGO`, `NBANDS`, `ENCUTGW`, `NOMEGA`, `LOPTICS`, `LSPECTRAL`, `ANTIRES`, `LADDER`, `LHARTREE`, `NBANDSV`, `NBANDSO`.
- `WAVECAR`, `WAVEDER`, `vaspout.h5`, response outputs, memory/resource logs.

## SimFlow guidance

- Treat GW/RPA/BSE as high-cost advanced methods; require dry-run/resource evidence and approval before execution.
- Do not present results as converged without explicit convergence series.
- Register predecessor chain, response settings, convergence tables, resource estimates, and scripts as artifacts.
- For BSE, record whether the workflow is optical-region BSE or core-excitation BSE.

## Common risks

- Too few empty bands or insufficient response cutoff.
- Missing predecessor compatibility.
- Single-shot advanced-method output treated as converged.
- Resource/memory failure mistaken for scientific failure.
