# VASP Official Sources

Use this reference to verify VASP-specific claims against official documentation. Prefer official sources before relying on memory, examples from older projects, or third-party blog posts.

## Core official entry points

- VASP Wiki main manual: https://www.vasp.at/wiki/Main_page
- VASP tutorials: https://www.vasp.at/tutorials/latest/
- py4vasp documentation: https://www.vasp.at/py4vasp/latest/
- VASP command-line arguments and dry runs: https://www.vasp.at/wiki/Command-line_arguments
- Optimizing parallelization: https://www.vasp.at/wiki/Optimizing_the_parallelization

## Input and output files

- INCAR: https://www.vasp.at/wiki/INCAR
- POSCAR: https://www.vasp.at/wiki/POSCAR
- POTCAR: https://www.vasp.at/wiki/POTCAR
- KPOINTS: https://www.vasp.at/wiki/KPOINTS
- Output files overview: https://www.vasp.at/wiki/Output
- OUTCAR: https://www.vasp.at/wiki/OUTCAR
- OSZICAR: https://www.vasp.at/wiki/OSZICAR
- vasprun.xml: https://www.vasp.at/wiki/Vasprun.xml
- vaspout.h5: https://www.vasp.at/wiki/Vaspout.h5
- EIGENVAL: https://www.vasp.at/wiki/EIGENVAL
- DOSCAR: https://www.vasp.at/wiki/DOSCAR
- CHGCAR: https://www.vasp.at/wiki/CHGCAR
- WAVECAR: https://www.vasp.at/wiki/WAVECAR

## High-value INCAR tag pages

- ENCUT: https://www.vasp.at/wiki/ENCUT
- EDIFF: https://www.vasp.at/wiki/EDIFF
- EDIFFG: https://www.vasp.at/wiki/EDIFFG
- NSW: https://www.vasp.at/wiki/NSW
- IBRION: https://www.vasp.at/wiki/IBRION
- ISIF: https://www.vasp.at/wiki/ISIF
- ISMEAR: https://www.vasp.at/wiki/ISMEAR
- SIGMA: https://www.vasp.at/wiki/SIGMA
- ISPIN: https://www.vasp.at/wiki/ISPIN
- MAGMOM: https://www.vasp.at/wiki/MAGMOM
- NELECT: https://www.vasp.at/wiki/NELECT
- NBANDS: https://www.vasp.at/wiki/NBANDS
- LREAL: https://www.vasp.at/wiki/LREAL
- LASPH: https://www.vasp.at/wiki/LASPH
- LORBIT: https://www.vasp.at/wiki/LORBIT
- NEDOS: https://www.vasp.at/wiki/NEDOS

## Advanced method pages

- DFT+U overview: https://www.vasp.at/wiki/DFT%2BU
- LDAU: https://www.vasp.at/wiki/LDAU
- LDAUL: https://www.vasp.at/wiki/LDAUL
- LDAUU: https://www.vasp.at/wiki/LDAUU
- LDAUJ: https://www.vasp.at/wiki/LDAUJ
- LSORBIT: https://www.vasp.at/wiki/LSORBIT
- LNONCOLLINEAR: https://www.vasp.at/wiki/LNONCOLLINEAR
- SAXIS: https://www.vasp.at/wiki/SAXIS
- LHFCALC: https://www.vasp.at/wiki/LHFCALC
- HFSCREEN: https://www.vasp.at/wiki/HFSCREEN
- LOPTICS: https://www.vasp.at/wiki/LOPTICS
- LEPSILON: https://www.vasp.at/wiki/LEPSILON
- ICHAIN: https://www.vasp.at/wiki/ICHAIN
- IMAGES: https://www.vasp.at/wiki/IMAGES
- IBRION phonon/vibration modes: https://www.vasp.at/wiki/IBRION
- MDALGO: https://www.vasp.at/wiki/MDALGO
- TEBEG: https://www.vasp.at/wiki/TEBEG
- TEEND: https://www.vasp.at/wiki/TEEND
- SMASS: https://www.vasp.at/wiki/SMASS

## Tutorial routes

Use official tutorials as workflow examples, not as universal parameter defaults. Select only the route relevant to the user request.

- Molecules: https://www.vasp.at/tutorials/latest/molecules/
- Bulk systems: https://www.vasp.at/tutorials/latest/bulk/
- Magnetism: https://www.vasp.at/tutorials/latest/magnetism/
- Molecular dynamics: https://www.vasp.at/tutorials/latest/md/
- Surfaces: https://www.vasp.at/tutorials/latest/surfaces/
- Transition states: https://www.vasp.at/tutorials/latest/transition_states/
- Hybrid functionals: https://www.vasp.at/tutorials/latest/hybrids/
- GW: https://www.vasp.at/tutorials/latest/gw/
- Bethe-Salpeter equation: https://www.vasp.at/tutorials/latest/bse/
- Phonons: https://www.vasp.at/tutorials/latest/phonons/
- Electron-phonon interactions: https://www.vasp.at/tutorials/latest/electron-phonon/
- Machine-learned force fields: https://www.vasp.at/tutorials/latest/mlff/
- Linear response: https://www.vasp.at/wiki/Category:Linear_response
- X-ray absorption spectroscopy: https://www.vasp.at/tutorials/latest/xas/
- Nuclear magnetic resonance: https://www.vasp.at/tutorials/latest/nmr/

## Calculation-class reference files

- Electronic minimization/static SCF: `vasp_calc_electronic_minimization.md`
- Structure optimization: `vasp_calc_structure_optimization.md`
- DOS and band structures: `vasp_calc_dos_band.md`
- Magnetism, DFT+U, SOC, noncollinear work: `vasp_calc_magnetism_dftu_soc.md`
- AIMD and MLFF: `vasp_calc_aimd_mlff.md`
- NEB and transition states: `vasp_calc_neb_transition_states.md`
- Phonons and electron-phonon: `vasp_calc_phonons_electron_phonon.md`
- Surfaces, adsorption, work functions, STM: `vasp_calc_surfaces_adsorption_stm.md`
- Defects and charged systems: `vasp_calc_defects_charged_systems.md`
- Hybrid/meta-GGA/vdW: `vasp_calc_hybrid_meta_vdw.md`
- GW/RPA/BSE: `vasp_calc_gw_rpa_bse.md`
- Optics, dielectric response, EELS: `vasp_calc_optics_dielectric_eels.md`
- XAS and core spectroscopy: `vasp_calc_xas_core_spectroscopy.md`
- NMR, EFG, hyperfine, response: `vasp_calc_nmr_efg_response.md`
- Wannier and post-processing: `vasp_calc_wannier_postprocessing.md`

## Source-use discipline

- When a parameter value or workflow rule matters scientifically, cite the official page used or note that it still needs verification.
- Treat tutorials as examples tied to their systems and VASP version context.
- If official fetch/search fails, return the official URL and mark the evidence as unverified instead of filling gaps from memory.
- Never quote or reproduce licensed POTCAR content. Only record metadata such as element order, flavor/date labels, ZVAL-derived NELECT, hashes when allowed, and local provenance notes.
