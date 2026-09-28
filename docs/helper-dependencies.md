# Standalone helper dependencies

Reading a Skill needs no Python installation. Running its optional scripts
requires Python 3.10+ and the libraries below. The pip project is a dependency
installer only; host packages carry the actual Skills, scripts, and resources.
From a source checkout, install the relevant extra with `python -m pip install
'.[cp2k]'`, replacing `cp2k` as appropriate. In an installed Skill package,
install from that Skill's `requirements.txt` instead. No runtime service is needed.

| Skill | Source extra | Dependencies / scope |
| --- | --- | --- |
| Modeling | `structure` | pymatgen, ASE; conventional cubic prototypes |
| CP2K | `cp2k` | ASE for CIF symmetry/cell conversion; other helpers use stdlib |
| LAMMPS | `lammps` | ASE for conversion, MDAnalysis for analysis |
| GPUMD/NEP | `gpumd` | pymatgen for structure generation |
| VASP | `vasp` | pymatgen, ASE, matplotlib for generation and plotting; parser uses stdlib |
| Analysis/visualization | `analysis` | NumPy, matplotlib, MDAnalysis, Pillow |
| Reference extraction | `reference-extraction` | See its existing requirements.txt |
| Computation, MLP | none | Python standard library |
| Literature review, proposal, writing | none | Guidance only |

The generator helpers prepare files; they neither launch simulations nor certify
scientific validity. Existing inputs and job scripts require explicit overwrite
options. NEP datasets are copied to train.xyz/test.xyz and models to nep.txt.
Use a separate calculation directory to avoid source/destination collisions.
