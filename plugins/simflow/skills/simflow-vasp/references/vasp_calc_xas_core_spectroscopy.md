# VASP Calculation Class: XAS and Core Spectroscopy

Use this reference for X-ray absorption spectroscopy, supercell core-hole workflows, and BSE core excitations.

## Official sources

- XAS tutorials: https://www.vasp.at/tutorials/latest/xas/
- Supercell core-hole calculations: https://www.vasp.at/wiki/Supercell_core-hole_calculations
- Bethe-Salpeter equation for core excitations: https://www.vasp.at/wiki/Bethe-Salpeter_equation_for_core_excitations
- XAS theory: https://www.vasp.at/wiki/XAS_theory
- CLNT: https://www.vasp.at/wiki/CLNT
- ICORELEVEL: https://www.vasp.at/wiki/ICORELEVEL

## Minimum evidence

- Method choice: supercell core-hole or BSE core excitation.
- Core level/edge, absorbing species/site, supercell size, core-hole pseudopotential or tag setup, and convergence plan.
- Predecessor requirements for BSE+GW-style core workflows when applicable.

## Tags and files to inspect

- Core-hole tags and setup, `NELECT`, `NBANDS`, k mesh, `LOPTICS`, `WAVECAR`, `vaspout.h5`, dielectric/spectrum outputs.
- For supercell core-hole workflows, dry-run setup evidence for electrons, bands, and k points.

## SimFlow guidance

- Treat XAS as advanced spectroscopy; require explicit method and convergence plan before execution.
- Register absorbing-site model, core-hole setup, spectrum data, broadening, alignment convention, and plot script.
- Do not compare spectra across cell sizes or alignments without recording the convention.
- Do not expose licensed POTCAR or core-hole potential content.

## Common risks

- Too small supercell for core-hole interactions.
- Unclear energy alignment or broadening.
- Missing edge/site provenance.
- Confusing supercell core-hole and BSE core-excitation assumptions.
