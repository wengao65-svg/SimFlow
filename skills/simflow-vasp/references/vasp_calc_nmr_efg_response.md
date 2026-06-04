# VASP Calculation Class: NMR, EFG, Hyperfine, and Response Properties

Use this reference for NMR chemical shielding, electric-field gradients, hyperfine coupling, magnetic susceptibility, and related response calculations.

## Official sources

- NMR tutorials: https://www.vasp.at/tutorials/latest/nmr/
- NMR category: https://www.vasp.at/wiki/NMR
- Calculating chemical shieldings: https://www.vasp.at/wiki/Calculating_the_chemical_shieldings
- Calculating electric field gradients: https://www.vasp.at/wiki/Calculating_the_electric_field_gradient
- Calculating the hyperfine-coupling constant: https://www.vasp.at/wiki/Calculating_the_hyperfine-coupling_constant
- Calculating the magnetic susceptibility: https://www.vasp.at/wiki/Calculating_the_magnetic_susceptibility
- LCHIMAG: https://www.vasp.at/wiki/LCHIMAG
- LEFG: https://www.vasp.at/wiki/LEFG

## Minimum evidence

- Well-converged structure and SCF predecessor; response properties can be highly sensitive to geometry.
- Target nucleus/isotope/site and experimental comparison convention.
- Insulating/metallic character and smearing choice.

## Tags and files to inspect

- `LCHIMAG`, `LEFG`, hyperfine-related tags, `ENCUT`, `EDIFF`, k mesh, `ISMEAR`, `SIGMA`, `ISTART`, `NELM`.
- `WAVECAR`, `OUTCAR`, `vaspout.h5`, response tensors, isotope constants, post-processing scripts.

## SimFlow guidance

- Record tensor conventions, reference compounds, isotope data, units, and comparison formulae.
- Treat response properties as post-SCF only when the predecessor is compatible and documented.
- Register raw tensor output, conversion scripts, and final tables as separate artifacts.
- Avoid response claims for metallic systems when the official method assumes insulating behavior.

## Common risks

- Loose structural convergence causing large EFG/shielding differences.
- Smearing settings inappropriate for NMR shieldings.
- Comparing different tensor conventions or reference scales.
- Missing restart/provenance for post-SCF response calculations.
