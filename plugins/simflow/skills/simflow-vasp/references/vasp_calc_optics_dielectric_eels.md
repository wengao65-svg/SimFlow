# VASP Calculation Class: Optics, Dielectric Response, Born Charges, and EELS

Use this reference for optical spectra, static/frequency-dependent response, dielectric tensors, Born effective charges, piezoelectric response, Raman/IR-related setup, and electron-energy-loss spectra.

## Official sources

- Linear response category: https://www.vasp.at/wiki/Category:Linear_response
- Optical/dielectric properties category: https://www.vasp.at/wiki/Optical_properties
- LOPTICS: https://www.vasp.at/wiki/LOPTICS
- LEPSILON: https://www.vasp.at/wiki/LEPSILON
- Born effective charges: https://www.vasp.at/wiki/Born_effective_charges
- Electron-energy-loss spectrum: https://www.vasp.at/wiki/Electron-energy-loss_spectrum
- LCALCEPS: https://www.vasp.at/wiki/LCALCEPS
- WAVEDER: https://www.vasp.at/wiki/WAVEDER

## Minimum evidence

- Target response: independent-particle optics, DFPT static dielectric tensor, Born charges, piezoelectric tensor, EELS, or Raman/IR-adjacent data.
- Converged ground-state predecessor and empty-band/convergence plan.
- Whether local-field effects, excitonic effects, SOC, or hybrid/GW/BSE corrections are intended.

## Tags and files to inspect

- `LOPTICS`, `LEPSILON`, `LCALCEPS`, `NBANDS`, `NEDOS`, `CSHIFT`, `WAVEDER`, `OMEGAMAX`, `LPEAD`, `ISMEAR`, `SIGMA`.
- `vaspout.h5`, `OUTCAR`, optical tensors, dielectric data, py4vasp output, custom plotted data.

## SimFlow guidance

- Record tensor component conventions, broadening/smearing, energy windows, and unit conversions.
- Do not interpret independent-particle optics as BSE-level spectra unless that workflow was run.
- For dielectric/Born-charge work, record structure relaxation quality and whether ions are clamped.
- Register response data and plot scripts separately from rendered figures.

## Common risks

- Too few empty bands for optical transitions.
- Metallic smearing or partial occupations creating invalid NMR/response assumptions.
- Missing WAVEDER consistency for multi-step optics workflows.
- Confusing macroscopic dielectric response, EELS, and excitonic spectra.
