# GPUMD/NEP Community Methodology

## Preamble

**Nature of this document.** The entries below are community-surfaced
reference suggestions, not established facts, not SimFlow endorsements, and
not universal recipes. They are organized as task-indexed operational guidance
with provenance type, confidence, and residual risk so the host can reason
about each value rather than apply it blindly.

**Verify before use.** Every parameter value, threshold, and strategy in this
document must be checked against the current version of the GPUMD/NEP official
manual and against your own system and version before use. SimFlow does not
assert the correctness of any value here; it only presents the guidance with
its provenance type and confidence.

**Confidence levels.**
- `high`: official manual confirms the behavior, or multiple independent
  community reports are consistent with the official documentation.
- `medium`: multiple community reports are consistent but lack direct official
  manual backing.
- `low`: isolated case, conflicting community reports, or pending
  verification.

**Source types.** Each entry carries one of: `official manual`,
`community experience`, `official manual + community experience`,
`historical record`. Source file paths, identities, and original conversation
content are intentionally omitted.

**Scope boundary.** General dataset coverage design, validation design,
active-learning readiness criteria, and production MLP-MD readiness criteria
belong to `simflow-mlp`. This document retains only GPUMD/NEP-specific
operational steps and provider-specific behavior; it does not redefine general
MLP methodology.

**Privacy.** This document contains no personal identity, contact
information, or raw conversation content.

---

## §1 Errors and Exceptions

This section indexes concrete error messages and abnormal phenomena reported in
the community, ordered by life-cycle stage (compile, run, train, post-process).
For each entry: stage, likely cause, diagnostic steps, fix, version or
environment notes, source type, confidence, and residual risk.

### ERR-01 `Error code: 700` / `an illegal memory access was encountered`

| Field | Value |
|---|---|
| Stage | MD run |
| Likely cause (ordered by frequency) | (1) NEP potential incomplete, atoms approach too closely, force blows up (~90% of cases); (2) initial structure has overlapping atoms or is otherwise non-physical; (3) genuine GPU memory exhaustion. Rarely a code bug. |
| Diagnostic steps | 1. Inspect `neighbor.out` for abnormally large neighbor counts. 2. Run one step with `ensemble nve` and `time_step 0` to isolate whether the initial structure itself is bad. 3. Check `nvidia-smi` for actual VRAM usage. |
| Fix | 1. Improve the NEP potential: add a short-range ZBL repulsive prior (see `zbl` and `use_typewise_cutoff_zbl`), and add high-temperature and large-deformation structures via active learning. 2. Optimize the initial structure. 3. Reduce `cutoff` (e.g. to `5 4`) to lower VRAM. |
| Version / environment | MD run stage; all versions. |
| Source type | official manual + community experience |
| Confidence | high |
| Residual risk | The same device error string can also originate from unrelated input, model, integration, or hardware conditions; do not assume the potential is always the cause. |

### ERR-02 `Error code: 209` / `no kernel image is available for execution on the device`

| Field | Value |
|---|---|
| Stage | Run / train |
| Likely cause | The `sm_xx` compute capability set in the `Makefile` at compile time does not match the physical GPU architecture on which the binary is running. |
| Diagnostic steps | Identify the actual GPU model and look up its Compute Capability. |
| Fix | Edit `CUDA_ARCH=-arch=sm_xx` in `src/makefile` to match the GPU (e.g. 4090 -> `sm_89`, A100 -> `sm_80`), then `make clean` and rebuild. |
| Version / environment | All. |
| Source type | community experience |
| Confidence | high |
| Residual risk | None if the architecture is matched correctly. |

### ERR-03 `nvcc fatal : Unsupported gpu architecture 'sm_xx'`

| Field | Value |
|---|---|
| Stage | Compile |
| Likely cause | The `sm_xx` value in the `Makefile` is too high for the installed CUDA toolkit. |
| Diagnostic steps | Run `nvcc --version` to check the CUDA compiler's supported architecture upper bound. |
| Fix | Edit `src/makefile`, lower `CUDA_ARCH=-arch=sm_xx` (e.g. on older CUDA with a 40-series card, try `sm_86` or `sm_80`), then `make clean` and rebuild. |
| Version / environment | Linux / WSL compile environments. |
| Source type | community experience |
| Confidence | high |
| Residual risk | None. |

### ERR-04 `The longest direction has less than 5 times of the NEP cutoff per GPU`

| Field | Value |
|---|---|
| Stage | MD run (single-node multi-GPU only. GPUMD does not currently support multi-node / cross-node parallelism; the multi-GPU path is restricted to GPUs within a single node.) |
| Likely cause | Under spatial decomposition, the simulation box dimension assigned to a single GPU is smaller than 5x the NEP cutoff, so the domain decomposition algorithm cannot satisfy its parallel-region partition requirement. |
| Diagnostic steps | Inspect the cell dimensions and the number of GPUs used on the single node. |
| Fix | (1) For systems below tens of thousands of atoms, prefer a single GPU. (2) If multiple GPUs are required, expand the cell (`replicate`) to increase the box dimension on the affected direction. |
| Version / environment | Multi-GPU MD within a single node. |
| Source type | official manual + community experience |
| Confidence | high |
| Residual risk | Blindly expanding the cell increases irrelevant compute cost; prefer fewer GPUs for sub-tens-of-thousands-atom systems. |

### ERR-05 `Cannot use triclinic box with only 3 target pressure components`

| Field | Value |
|---|---|
| Stage | MD run |
| Likely cause | The simulation box is triclinic (non-orthogonal) but the barostat command (e.g. `npt_scr` or `npt_mttk`) was given only 3 target pressure values. |
| Diagnostic steps | Inspect whether the `Lattice` matrix in `model.xyz` has non-zero off-diagonal elements. |
| Fix | For a triclinic cell, supply all 6 stress components as target values (e.g. `x y z yz xz xy`). |
| Version / environment | NPT barostat simulation. |
| Source type | community experience |
| Confidence | high |
| Residual risk | None. |

### ERR-06 `Cannot use 6 pressure components with non-periodic boundary in any direction`

| Field | Value |
|---|---|
| Stage | MD run |
| Likely cause | A pressure component is being applied on a non-periodic direction (e.g. `pbc="T T F"`). |
| Diagnostic steps | Inspect the `pbc` setting on the first line of `model.xyz` and the `npt` command in `run.in`. |
| Fix | Non-periodic directions cannot be pressure-controlled. Apply independent pressure control only to periodic directions (e.g. drop the z-axis pressure control). |
| Version / environment | NPT with out-of-plane non-periodic boundaries. |
| Source type | community experience |
| Confidence | high |
| Residual risk | None. |

### ERR-07 MD structural collapse / explosion or temperature spike

| Field | Value |
|---|---|
| Stage | MD run |
| Likely cause | The model has entered an extrapolation region absent from the training set; the integration time step is too large; or the high-temperature regime lacks a sufficient short-range repulsive barrier. |
| Diagnostic steps | View the trajectory in OVITO; check whether atoms are overlapping or flying out of the box. |
| Fix | 1. Add `zbl 2.5` and `use_typewise_cutoff_zbl 0.7` in `nep.in`. 2. Reduce `time_step` (e.g. from 1 fs to 0.5 fs). 3. Extract the structure a few frames before collapse and add it to the training set, then retrain. |
| Version / environment | High-temperature / large-deformation MD. |
| Source type | community experience |
| Confidence | high |
| Residual risk | None. |

### ERR-08 `Warning: There is energy < -100 eV/atom in the data set.`

| Field | Value |
|---|---|
| Stage | NEP training |
| Likely cause | The absolute energies in the training set are very large (typical for CP2K or ABACUS data), so under NEP's single-precision (FP32) computation significant digits are lost and the energy signal is buried in numerical noise. |
| Diagnostic steps | Inspect the terminal warning; check whether the energy RMSE in `energy_train.out` stays high. |
| Fix | Apply an **energy shift**: subtract a per-atom average reference energy from every structure (or align to the NEP89 zero reference) using a `gpumdkit.sh -shift_energy`-style script or `NepTrainKit`. |
| Version / environment | NEP training with non-VASP DFT data. |
| Source type | official manual + community experience |
| Confidence | high |
| Residual risk | An incorrect shift can hide a label mismatch or break comparability with a foundation model. |

### ERR-09 `type in nep.in has not been set`

| Field | Value |
|---|---|
| Stage | NEP training |
| Likely cause | The `type` keyword is missing from `nep.in`, or the file was edited on Windows and carries invisible `\r\n` carriage returns that Linux cannot parse. |
| Diagnostic steps | Run `cat -v nep.in` and look for `^M` markers. |
| Fix | Add `type N El1 El2 ...`; on a Windows-edited file, run `dos2unix nep.in` to convert line endings. |
| Version / environment | Windows-to-Linux training file transfer. |
| Source type | community experience |
| Confidence | high |
| Residual risk | None. |

### ERR-10 NEP training initial `Total Loss` is `nan`

| Field | Value |
|---|---|
| Stage | NEP training |
| Likely cause | (1) The training set contains severely non-physical structures with infinite forces. (2) Probabilistic numerical overflow under multi-GPU training (a spurious error). |
| Diagnostic steps | Check whether multi-GPU training is in use; inspect `train.xyz` for any force exceeding ~100 eV/A. |
| Fix | 1. Re-run on a single GPU to test. 2. Clean the training set with `NepTrainKit` to remove outliers. |
| Version / environment | Multi-GPU NEP training. |
| Source type | community experience |
| Confidence | medium |
| Residual risk | The multi-GPU `nan` may be transient and disappear on retry. |

### ERR-11 `Segmentation fault (core dumped)` during fine-tune restart

| Field | Value |
|---|---|
| Stage | NEP training / scripts |
| Likely cause | (1) A second fine-tune step was started without removing the `fine_tune` command from `nep.in`. (2) A Python script is reading a file that is still being written or has truncated rows. |
| Diagnostic steps | Inspect whether `nep.in` still contains `fine_tune` on a second-stage continuation; check whether data files have a missing trailing newline. |
| Fix | When continuing after a fine-tune interruption, delete the `fine_tune` statement and read `nep.restart` for an ordinary continuation. |
| Version / environment | NEP fine-tune continuation. |
| Source type | community experience |
| Confidence | high |
| Residual risk | None. |

### ERR-12 `stress_train.out` or `virial_train.out` filled with `-1e+06`

| Field | Value |
|---|---|
| Stage | Post-processing |
| Likely cause | The dataset does not actually contain stress or virial labels; NEP writes `-1e+06` as the missing-value sentinel. |
| Diagnostic steps | Inspect the `Properties=` field on line 2 of `train.xyz` for a virial declaration. |
| Fix | This is expected behavior. If virials are not needed, ignore the values. If they are needed, re-prepare the training set with virial-labeled DFT data. |
| Version / environment | NEP prediction output. |
| Source type | official manual + community experience |
| Confidence | high |
| Residual risk | None. |

### ERR-13 `Error code: 100` / `no CUDA-capable device is detected`

| Field | Value |
|---|---|
| Stage | Run / train |
| Likely cause | The system or environment cannot see an NVIDIA GPU. Usually a missing or mismatched driver, or a WSL configuration problem. |
| Diagnostic steps | Run `nvidia-smi` and verify GPU output. On HPC, confirm a GPU node has actually been allocated. |
| Fix | Reinstall or update the NVIDIA driver and matching CUDA Toolkit; on HPC, ensure the scheduler has assigned a GPU node. |
| Version / environment | Software / hardware environment configuration. |
| Source type | community experience |
| Confidence | high |
| Residual risk | None. |

### ERR-14 `Error code: 222` / `the provided PTX was compiled with an unsupported toolchain`

| Field | Value |
|---|---|
| Stage | Run / train |
| Likely cause | The CUDA Toolkit version used to compile is higher than what the system's NVIDIA driver supports. |
| Diagnostic steps | Compare `nvcc -V` (compile-time version) against the maximum supported CUDA version shown in the `nvidia-smi` header. |
| Fix | Downgrade the CUDA Toolkit (e.g. to 11.8 or 12.1), or upgrade the NVIDIA driver to support a higher CUDA. |
| Version / environment | All. |
| Source type | community experience |
| Confidence | high |
| Residual risk | None. |

### ERR-15 `Thrust requires at least C++17` or related C++14 errors

| Field | Value |
|---|---|
| Stage | Compile |
| Likely cause | Newer CUDA (e.g. 13.0+) ships a Thrust library that requires C++17, but the `Makefile` defaults to `-std=c++14` or `-std=c++11`. |
| Diagnostic steps | Inspect the compile log for `cpp_dialect.h` and C++ version requirements. |
| Fix | Edit `src/makefile`, change `-std=c++14` in `CFLAGS` to `-std=c++17`, then rebuild. |
| Version / environment | CUDA 13.0+. |
| Source type | community experience |
| Confidence | high |
| Residual risk | None. |

---

## §2 NEP Training Methodology and Parameters

### Parameter table

The table below lists community-surfaced default ranges. Every value must be
validated against the official manual for the installed version and against the
target system.

| Parameter | File | Recommended range | Rationale (algorithmic or physical) | Applicability | Wrong-setting consequence | Check method | Source type | Confidence |
|---|---|---|---|---|---|---|---|---|
| `cutoff` | `nep.in` | Default `8 4`. Per-system starting values:<br>- **Metals / semiconductors**: start from `6 4` or `5 5`.<br>- **Liquid water / aqueous solutions**: typically `6 4`.<br>- **Charged systems (qNEP)**: reduce to `5 5` or `6 4`. Long-range electrostatics is handled by the physical model (Ewald summation); shortening the potential cutoff forces the model to focus on local chemistry and is often better. | An oversized cutoff introduces long-range noise, inflates VRAM, and slows MD; NEP's descriptors are efficient and do not require large cutoffs. For qNEP, the long-range part is owned by Ewald so a smaller NN cutoff is beneficial. | All NEP training. | VRAM OOM; MD slowdown; unstable model under same dataset. | See "How to judge `cutoff`" below. | official manual + community experience | high |
| `n_max` / `basis_size` | `nep.in` | Defaults `4 4` and `8 8`. For high-precision needs raise to `6 6 / 10 10` or even `9 7 / 12 8`. | Control descriptor resolution (polynomial and basis-function count). Larger values raise resolution but also parameter count and compute cost. | Complex systems (liquids, multi-element alloys, high-precision needs). | Oversized values increase compute and parameter count, inviting overfitting or slowdown. | Balance training RMSE against compute speed. | official manual + community experience | high |
| `l_max` | `nep.in` | Default `4 2 0` (5-body off). For very high precision can be set to `4 2 1` or `4 2 2`. | Sets the maximum expansion order of 3-, 4-, 5-body descriptors. Enabling 5-body multiplies compute cost. | Liquid systems strongly recommend keeping `0` (5-body off). | Enabling 5-body sharply slows MD. | Inspect `loss.out` for whether the precision gain justifies the speed loss. | official manual + community experience | high |
| `neuron` | `nep.in` | Default `30`. Typically `30-50` is sufficient; with very rich datasets can rise to `80-100`. | Hidden-layer neuron count. NEP's parameter count is far smaller than deep-learning potentials like MACE; an oversized network barely improves precision but slows MD. | All NEP training. | Oversized network barely improves precision and slows MD. | Compare test-set prediction error. | official manual + community experience | high |
| `batch` | `nep.in` | Typically `1000-2000`. The SNES evolution strategy strongly prefers **full batch** (batch >= total structure count in the training set). | SNES performs global gradient approximation; large batch removes gradient noise and helps the model reach the true minimum of the potential-energy surface. | Whenever VRAM permits. | Too small (e.g. 32) -> late-stage loss oscillation and slow convergence; too large -> VRAM OOM. | Inspect whether the late-stage `loss.out` curve converges smoothly. | community experience | high |
| `generation` | `nep.in` | From-scratch: typically `100000-200000` steps. Foundation-model fine-tune: typically `10000-20000` steps. | Insufficient steps -> underfitting; excessive fine-tune steps -> catastrophic forgetting of the foundation model. | All NEP training. | See consequence column. | Inspect whether `loss.out` has flattened. | official manual + community experience | high |
| `lambda_e`, `lambda_f`, `lambda_v` | `nep.in` | Base training keep default `1.0 : 1.0 : 0.1`. Two-step second stage: `e=5-10`, `f=1`, `v=0.5-1`. Liquid systems: `v=0`. | NEP's loss uses **RMSE (root-mean-square error), not MSE**. The square root already balances the magnitude difference between energy and force; setting `lambda_f` to extreme values (e.g. 100 or 10000, as in some other codes) breaks regularization and distorts the model. | Most ambient-pressure dense systems. | Extreme force weight breaks regularization and distorts the model; forcing virial fit in liquids backfires precision. | Inspect whether each error term in `loss.out` decreases in balance. | official manual + community experience | high |
| `lambda_1`, `lambda_2` | `nep.in` | Base training: leave default (do not write). On restart with `nep.restart`: **strongly add `lambda_1 0`**. | L1 regularization drives parameters toward zero ("sparsification"). SNES maintains a per-parameter mean and variance (effectively a dynamic learning rate). After stage one, L1 has pushed many parameters to ~0, so their dynamic learning rate also drops to ~0; on restart those parameters cannot reactivate. Setting `lambda_1 0` releases this penalty so all parameters can update freely under the new loss weights. | All restart / continuation training. | Restart without `lambda_1 0` -> RMSE anomalously jumps. | Inspect whether RMSE abnormally jumps after restart. | official manual + community experience | high |
| `zbl` + `use_typewise_cutoff_zbl` | `nep.in` | Strongly recommended: `zbl 2.5` with `use_typewise_cutoff_zbl 0.7`. | Analytic ZBL short-range repulsive prior takes over at very short distances, preventing the model from emitting a spurious attractive force or zero force when atoms approach closely under high temperature or collision. | High-temperature, collision, irradiation, active-learning, liquid systems. | Without it, high-temperature MD collapses instantly. | Run a high-temperature (e.g. 2000K+) NVT test for collapse. | official manual + community experience | high |
| `type_weight` | `nep.in` | For a minority species (e.g. few solute ions in water), assign a higher weight (e.g. `10`). | Without a higher weight, the model minimizes global error by ignoring the few minority-species atoms; the solution force field fails for the solute. | Compositionally imbalanced datasets. | Without it, the model "ignores" the minority species. | Inspect per-species prediction error. | community experience | high |
| `force_delta` | `nep.in` | When the dataset mixes extreme high-force and equilibrium structures, consider `force_delta 0.1`. | Down-weights the contribution of very large forces in RMSE so that a few extreme-force points do not dominate and sacrifice equilibrium-region fitting. | Radiation damage, deposition, high-pressure mixed datasets. | Too large -> the delta mechanism has no effect; force-fitting extremely close dimers degrades overall precision. | Inspect whether equilibrium-region RMSE improves. | community experience | medium |

### How to judge whether `cutoff` is reasonable

**Neighbor-count rule (core experience).** Observe the neighbor counts reported
by the training program. As a rule of thumb, **radial neighbors around 100** and
**angular neighbors around 30-50** are reasonable balance points. If
`neighbor.out` shows the actual neighbor count approaching or exceeding the
maximum, or exceeding **75% of the maximum**, the potential has likely entered
an extrapolation region and the structure is unstable.

**Precision vs speed test.** A larger cutoff is not always better. An oversized
cutoff introduces extra noise features that require more dataset coverage;
otherwise the model becomes *less* stable under the same dataset. When testing,
start from the default and scan with **0.5 A intervals** (e.g. `6 4`, `5.5 4`,
`5 4`), running multiple short trainings and comparing whether the loss
converges smoothly and whether MD collapses.

### REC-TWOSTEP Two-step training

**Goal.** Without sacrificing force accuracy, substantially raise energy and
virial accuracy.

**Applicability.** Ambient-pressure dense solids, crystals, conventional
alloys. **Not applicable** to MACE / DeePMD / NequIP / Allegro or any other
trainer; the two-step policy is NEP-specific.

**Why it works (algorithmic mechanism).** NEP's loss uses RMSE. By the end of
stage one, the force RMSE has typically hit a plateau, and the energy term's
absolute value is already small; with the default `lambda_e = 1.0`, the energy
contribution to the total loss becomes negligible and is dominated by
regularization. In stage two, raising `lambda_e` to 5-10 forces the network to
redirect remaining optimization capacity onto the energy error. Combined with
full batch, this typically lowers energy RMSE by about an order of magnitude
while force accuracy is barely affected.

**Stage one `nep.in` (foundation)**:
```text
type 2 Si C
cutoff 6 4
n_max 4 4
basis_size 8 8
l_max 4 2 0
neuron 30
lambda_e 1.0
lambda_f 1.0
lambda_v 0.1
batch 1000
generation 100000
```

**Stage two `nep.in` (continuation; keep `nep.restart` in place)**:
```text
type 2 Si C
cutoff 6 4
n_max 4 4
basis_size 8 8
l_max 4 2 0
neuron 30
lambda_1 0          # required: disable L1 so stage-one parameters can reactivate
lambda_e 5.0        # core: raise energy weight to 5-10
lambda_f 1.0        # keep force weight at 1.0
lambda_v 1.0        # raise if stress / elastic constants matter
batch 5000          # full batch (>= total structure count)
generation 50000
```

| Field | Value |
|---|---|
| Source type | official manual (restart and loss parameters) + community experience |
| Confidence | high |
| Residual risk | Accidentally leaving `fine_tune` in stage two causes `core dumped`; an unshifted energy reference causes loss to diverge. |
| Verify before use | Confirm the official manual's current description of `nep.restart`, `lambda_*`, and `fine_tune`. |

---

## §3 Dataset Construction and Active Learning

This section captures GPUMD/NEP-specific operational steps. General dataset
coverage design, validation-set design, and production MLP-MD readiness criteria
belong to `simflow-mlp`.

### DS-01 AIMD sampling redundancy and high cost

| Field | Value |
|---|---|
| Problem | Naively feeding every frame of a continuous AIMD trajectory into the training set is wasteful and produces highly homogeneous data. |
| Suggestion | Pre-sample with a classical force field, a semi-empirical method, or a general large model (NEP89, MACE), then down-sample with Farthest-Point Sampling (FPS) before running DFT single-points. |
| Algorithmic rationale | Adjacent AIMD frames are highly similar; redundant frames bias the model toward local regions of the PES without expanding coverage. |
| Applicability | Complex liquids, large-system phase transitions, high-temperature melting, long-time sampling. |
| Check method | Inspect a PCA/UMAP projection or run FPS and observe whether most structures cluster tightly. |
| Recommended action | Run target MD -> use `NepTrainKit` FPS to extract tens to a few hundred most-different structures -> compute high-precision DFT single-points -> merge into `train.xyz`. |
| Source type | community experience |
| Confidence | high |
| Residual risk | Over-pruning can drop rare but important configurations. |

### DS-02 CP2K / ABACUS data requires energy shift

| Field | Value |
|---|---|
| Problem | Training on CP2K or ABACUS data yields very large errors and fails to converge, often accompanied by the `energy < -100 eV/atom` warning. |
| Suggestion | Apply an **energy shift**: subtract a per-atom average reference energy from every structure, or align to the NEP89 zero reference. |
| Physical rationale | NEP uses **single-precision (FP32)** arithmetic for speed. CP2K / ABACUS total energies have very large absolute magnitudes (e.g. -140000 eV), which consume the limited mantissa of FP32 and bury the small per-structure energy differences in numerical noise. |
| Applicability | Non-VASP DFT data, especially CP2K, ABACUS, QE. |
| Check method | Terminal warning `energy < -100 eV/atom`; energy RMSE in `loss.out` stuck high. |
| Recommended action | Use `gpumdkit.sh -shift_energy` or `NepTrainKit` to shift `train.xyz` toward 0. |
| Source type | official manual + community experience |
| Confidence | high |
| Residual risk | An incorrect shift can hide a label mismatch or break comparability with a foundation model. |

### DS-03 Insufficient temperature / strain configuration coverage

| Field | Value |
|---|---|
| Problem | Training only on near-equilibrium structures leaves the model with no extrapolation capability; MD collapses (Error 700) on the first large fluctuation. |
| Suggestion | "Up-sample" the dataset: include thermal-fluctuation configurations above the target temperature (even above the melting point), and deliberately introduce volume strain (e.g. +-3% to +-5%) plus random atomic-coordinate perturbations (e.g. 0.1 A). |
| Physical rationale | The model must learn the PES away from the equilibrium basin; otherwise any unseen fluctuation drives it into a non-physical region. |
| Applicability | All systems that need high-temperature phase transitions, thermal conductivity, elastic constants, or thermal expansion. |
| Check method | Compute target-temperature elastic constants or run NPT and observe whether the volume abnormally expands or the phase-transition temperature is far off. |
| Recommended action | Generate a series of scaled + perturbed configurations from the optimized cell; sample at above-target-temperature MD. |
| Source type | community experience |
| Confidence | high |
| Residual risk | If only equilibrium structures are added after cell expansion, compute cost rises with little gain. |

### DS-04 Defects, interfaces, surfaces

| Field | Value |
|---|---|
| Problem | Bulk-only data cannot describe defect or interface chemistry; atoms may unphysically intermix or aggregate at the interface. |
| Suggestion | For a heterostructure, include: A-phase bulk + B-phase bulk + A/B interface models, with varied interface spacings, stackings, and vacancy types. |
| Physical rationale | Missing interface data leads to non-physical intermixing or aggregation; missing specific defects can break local charge or PES correctness. |
| Applicability | Solid-solid interface heat transport, surface adsorption, catalysis, polycrystalline grain boundaries, vacancy / interstitial irradiation. |
| Check method | Use NEP to predict DFT single-point energies of the interface / defect; if RMSE is very large, the environment is missing. |
| Recommended action | Manually build supercells with different interface spacings, stackings, and vacancies, perturb them, then compute DFT and add to the training set. |
| Source type | community experience |
| Confidence | high |
| Residual risk | None. |

### DS-05 Is a test set required for NEP training?

| Field | Value |
|---|---|
| Conclusion | **The NEP training algorithm implementation does not consume `test.xyz` for parameter updates.** The program reads it only to emit prediction-error diagnostics and parity plots; it has no effect on weight evolution. This is an objective behavior of the NEP source code and is unrelated to the general deep-learning practice of holding out a validation set to prevent overfitting. |
| Rationale | In the NEP training source, the `test.xyz` prediction error is used only for diagnostic output; it does not enter the loss function or the gradient-update path. |
| Applicability | All NEP training tasks. |
| Recommended action | For datasets smaller than ~2000 structures, place all data in `train.xyz`; do not sacrifice training diversity to draw a test-set parity plot. |
| Common mistake | Treating a low test-set RMSE as proof of high generalization ability. |
| Real validation | Run long MD at the target temperature and pressure and check RDF / MSD / elastic constants / density against experiment or DFT. |
| Source type | community experience |
| Confidence | high |
| Residual risk | This behavior is NEP-specific; do not extrapolate to MACE / DeePMD / NequIP / Allegro, which do use validation sets for early stopping. |
| Verify before use | Confirm against the current NEP source and official manual for the role of `test.xyz`. |

### DS-06 Outlier (bad-point) detection and handling

| Field | Value |
|---|---|
| Problem | DFT non-converged structures, very large forces (>50 eV/A), or severely overlapping atoms distort the entire PES fit if forced into the training set. |
| Suggestion | Inspect the parity plot; do not force NEP to fit these points. Remove them, or for genuinely large-but-physical forces tune `force_delta 0.1` in `nep.in`. |
| Physical rationale | Under RMSE, a few very-large-force outliers occupy a disproportionate weight and force the model to sacrifice equilibrium-region fitting to accommodate them. |
| Applicability | High-temperature collision, radiation damage, active-learning blind-guess phase. |
| Check method | `force_train.out` or `NepTrainKit` parity plot shows isolated far-off points. |
| Recommended action | Delete non-physical outliers; for reasonable large forces, tune `force_delta`. |
| Source type | community experience |
| Confidence | high |
| Residual risk | Over-pruning legitimate high-force configurations weakens short-range description. |

### DS-07 Active learning from MD collapse

| Field | Value |
|---|---|
| Problem | GPUMD run interrupted by bond-breaking, atom ejection, or explosion indicates the model has entered an unknown region. |
| Suggestion | Do not extract fully shattered frames (atoms <1 A apart); instead extract **the critical pre-collapse frames** (1-5 frames before collapse) and compute DFT single-points on them. |
| Physical rationale | Fully collapsed frames have atoms too close for DFT to converge or contain unphysical error that contaminates the dataset. |
| Applicability | Active-learning iteration when the current potential survives only tens of ps before collapse. |
| Check method | Inspect whether `neighbor.out` neighbor counts spike, or check structural reasonableness in OVITO a few frames before collapse. |
| Recommended action | Extract pre-collapse frames, compute accurate DFT, add to `train.xyz`, retrain (iterative expansion). |
| Source type | community experience |
| Confidence | high |
| Residual risk | None. |

### DS-08 Close-dimer trap

| Field | Value |
|---|---|
| Problem | Adding many very-close dimers (e.g. <1-1.4 A) to the training set to "teach" short-range repulsion. |
| Suggestion | Do not force-close dimers into the training set; let the analytic ZBL prior (`zbl` + `use_typewise_cutoff_zbl`) take over at very short range. |
| Physical rationale | Conventional DFT functionals are inaccurate at extremely close interatomic distances; forcing NEP to learn inaccurate short-range repulsion degrades equilibrium-region accuracy. |
| Applicability | Radiation damage, high-temperature high-pressure collision systems. |
| Check method | After adding very-close dimers, check whether the regular-force region (-5 to 5 eV/A) RMSE deteriorates significantly. |
| Recommended action | Enable `zbl` and `use_typewise_cutoff_zbl` instead of relying on DFT at extreme close range. |
| Source type | community experience |
| Confidence | high |
| Residual risk | None. |

### Golden rules summary

1. **Diversity over redundancy.** 100 configurations covering strain, defects,
   high temperature, and perturbation are worth more than 10000 near-equilibrium
   vibrating configurations.
2. **Test by MD, not by RMSE.** A potential is reliable only after surviving
   several ns of MD at the target conditions without unphysical phase
   transitions or collapse, and after reproducing elastic constants and RDF.
3. **Do not torture DFT.** Atomic-overlap configurations are inaccurate in DFT;
   let ZBL handle them.

---

## §4 RMSE-vs-MD Failure Deep-Dive

### PHEN-01 Training / test RMSE is very low but MD collapses or properties are wrong

**Typical phenomena.**
- The parity plot looks perfect (R^2 ~ 1, energy error <1 meV/atom), but within
  a few ps of NVT or NPT the atoms collapse or fly out of the box, raising
  `Error 700`.
- A few-hundred-atom cell runs stably, but expanding to tens of thousands of
  atoms causes rapid collapse.
- MD does not crash, but elastic constants (e.g. low C44), phonon spectra
  (imaginary modes), melting points (off by hundreds of K), or thermal
  conductivity diverge from experiment or DFT.

**Likely causes.**
1. **Severe overfitting and homogeneous data.** The training set contains only
   near-equilibrium structures, so the model memorizes known points. RMSE
   drops to ~0 but extrapolation capability is gone; any unseen configuration
   produces a wildly wrong force.
2. **Missing short-range physical protection.** The system undergoes
   high-temperature collision or large deformation absent from the training
   set, and `nep.in` lacks a ZBL repulsive prior; atoms approach closely and
   the model emits a spurious attractive or zero force, causing collapse.
3. **Hidden DFT data errors.** CP2K / ABACUS absolute energies lose precision
   under FP32; or K-point density / SCF convergence criteria are inconsistent
   across structures, so the model fits contradictory data.

**Why RMSE alone is not a reliability standard.**
- **RMSE reflects only interpolation.** It measures the fit on the (possibly
  very limited) sampled points. If the true PES is complex but sampling points
  all sit near the equilibrium basin, an RMSE of 0 still permits non-physical
  oscillation in unsampled regions; MD quickly falls into these false wells.
- **Error-cancellation illusion.** With very diverse data the model is forced
  to compromise, raising overall RMSE; yet random errors can cancel and produce
  better macroscopic thermodynamic predictions (density, RDF) than a
  low-RMSE overfit model.

**Dataset checks.**
- Use `gpumdkit.sh -min_dist train.xyz` to check minimum inter-atomic
  distances (<1.0 A is non-physical) and maximum forces (>50 eV/A is an
  outlier).
- If all forces lie in +-2 eV/A, the structures lack thermal fluctuation and
  deformation; extrapolation will fail.
- Verify energy-reference consistency (energy shift applied for non-VASP
  data); verify `ENCUT`, `KSPACING`, and SCF convergence are uniform across
  all configurations.

**MD stability tests.**
- Run several hundred ps to a few ns at the target (and higher) temperature
  under NVT and NPT; inspect `thermo.out` for energy / volume jumps or drift.
- Inspect `neighbor.out`. If the actual `angular` maximum neighbor count
  persistently exceeds 75% of the allowed maximum, or climbs over time, the
  system is approaching an extrapolation region and will likely collapse.

**Structure-supplementation strategy.**
- **High-temperature configurations:** use NEP89 or a classical force field to
  run high-temperature MD (above the melting point), sample, and compute DFT.
- **Strain / extreme-pressure configurations:** scale the cell by +-5% volume
  and apply shear to correct elastic-modulus and pressure response.
- **Defects and interfaces:** if the target involves fracture, adsorption, or
  phase transition, include vacancies, surfaces, and solid-liquid interface
  configurations.

**Community cases (illustrative).**
- Organic small-molecule reactions: low-intensity perturbation only -> very
  low RMSE but polymer decomposition MD diverges immediately. Solved by adding
  high-temperature AIMD samples.
- Water-graphene heterostructure: stable at 200 atoms, but collapses after
  cell expansion to tens of thousands of atoms. Solved by adding high-temperature
  heterostructure single-point energies.
- Silicon system: NEP force RMSE is slightly higher than GAP, but the NEP PES
  is smoother and predicts thermal conductivity and phonon spectra far better
  than an overfit low-RMSE model.

| Field | Value |
|---|---|
| Source type | community experience |
| Confidence | high |
| Residual risk | When long-wavelength phonons of a large cell are not covered by the training set, small-cell tests cannot expose the failure. |
| Verify before use | Always validate the final potential by long MD at the target conditions. |

---

## §5 Cookbook Recipes

Six classic GPUMD/NEP use cases with complete `nep.in` / `run.in` snippets.
Each is marked as a community-surfaced recipe, not a SimFlow endorsement. Real
execution and submission remain safety-gated and are not performed by this
skill.

### REC-01 From-scratch NEP training with two-step precision boost

**Goal.** Train a NEP potential from DFT data, then use the two-step method to
simultaneously achieve very high force and energy / virial accuracy.

**Applicability.** Most solids, crystals, and conventional alloys.

**Inputs.** `train.xyz`, optional `test.xyz`, `nep.in`.

**Stage-one `nep.in`.**
```text
type 4 C H Mg O
cutoff 6.0 4.0
zbl 2.5
use_typewise_cutoff_zbl 0.7
lambda_e 1.0
lambda_f 1.0
lambda_v 0.1
batch 1000
generation 100000
```

**Stage-two `nep.in` (continuation).**
```text
type 4 C H Mg O
cutoff 6.0 4.0
zbl 2.5
use_typewise_cutoff_zbl 0.7
lambda_1 0
lambda_e 5.0
lambda_f 1.0
lambda_v 1.0
batch 5000
generation 50000
```

**Key parameters.** `cutoff`, `zbl` short-range repulsion, `lambda_e/f/v` loss
weights, `lambda_1 0` restart protection.

**Steps.**
1. Prepare an energy-shifted `train.xyz`.
2. Configure stage-one `nep.in` and run `nep`.
3. After stage one, without deleting any files, edit `nep.in` (raise energy
   weight, full batch, disable L1) and run `nep` again for high-precision
   continuation.

**Outputs.** `nep.txt`, `loss.out`, `force_train.out`, etc.

**Sanity check.** In `loss.out`, energy / force / virial error curves converge
smoothly; energy RMSE typically <5 meV/atom, force RMSE typically <50-100
meV/A depending on the system.

**Common errors.** Forgetting to shift CP2K / ABACUS absolute energies ->
FP32 precision loss and large errors; omitting `zbl` -> structural collapse.

**Community warning.** NEP uses RMSE and naturally balances energy / force
magnitudes; do **not** set `lambda_f` to hundreds or tens of thousands as in
DP / MACE.

| Field | Value |
|---|---|
| Source type | community experience |
| Confidence | high |
| Residual risk | Stage-two `fine_tune` left in causes `core dumped`; unshifted energy causes loss divergence. |

### REC-02 HNEMD lattice thermal conductivity

**Goal.** Compute three-dimensional lattice thermal conductivity via
Homogeneous Non-Equilibrium Molecular Dynamics (HNEMD).

**Applicability.** Bulk insulators, semiconductors, solid alloys.

**Inputs.** `model.xyz`, `run.in`, `nep.txt`.

**`run.in` snippet.**
```text
potential nep.txt
velocity 300
time_step 1
# 1. NVT equilibration
ensemble nvt_nhc 300 300 100
run 100000
# 2. HNEMD production
compute_hnemd 1000 0 0 1.0e-4
run 2000000
```

**Key parameters.** `ensemble` thermostat, `compute_hnemd` driving force
magnitude (e.g. `1.0e-4` A^-1), total `run` steps.

**Steps.**
1. Equilibrate at the target temperature with `nvt_nhc` for enough steps.
2. Apply the driving force via `compute_hnemd` and run several million more
   steps.
3. Extract results; use an official or community Python script
   (`plot_kappa_shc.py`) to average and visualize.

**Outputs.** `thermo.out`, `kappa.out`, `shc.out`.

**Sanity check.** `kappa.out` thermal-conductivity curve converges smoothly
with time (no divergence); the cumulative integral of `shc.out` matches
`kappa.out`.

**Common errors.** Driving force `Fe` too large -> non-linear response or
structural damage; too small -> very low signal-to-noise, wild curve.

**Community warning.** For isotropic materials, run separately along x, y, z
(or apply independent driving forces simultaneously) and average to reduce
error.

| Field | Value |
|---|---|
| Source type | official manual + community experience |
| Confidence | high |
| Residual risk | None. |

### REC-03 NEP-based phonon dispersion

**Goal.** Quickly extract the zero-temperature phonon dispersion to verify
the MLP in the harmonic regime.

**Applicability.** Crystalline materials, solid alloys.

**Inputs.** `model.xyz` (expanded supercell), `run.in`, `nep.txt`,
`basis.in`, `kpoints.in`.

**`run.in` snippet.**
```text
potential nep.txt
# high-precision relaxation
minimize fire 1.0e-8 100000 1
# phonon calculation: force-constant cutoff 10 A, displacement 0.01 A
compute_phonon 10 0.01
```

**Key parameters.** Force-constant cutoff (must be >= 2x the NEP `cutoff`);
finite displacement (typically `0.01` A).

**Steps.**
1. Expand the primitive cell into a supercell thick enough (>2x the
   force-constant cutoff).
2. Run high-precision energy minimization (`minimize fire`) to reach the
   ground state.
3. Call `compute_phonon`.
4. Post-process with `create_phonon_compare.py` or the Calorine library.

**Outputs.** `D.out` (dynamical matrix), `phonon.out` (phonon frequencies).

**Sanity check.** Acoustic branches strictly tend to 0 at Gamma; no
non-physical imaginary modes.

**Common errors.** Errors or imaginary modes usually mean the supercell is
too small (e.g. only 15 A thick) to accommodate long-wavelength phonons or
long-range force constants.

**Community warning.** NEP does not include non-analytic / long-range Coulomb
corrections (Born Effective Charge) by default. For polar-bond materials,
additional handling or qNEP is required.

| Field | Value |
|---|---|
| Source type | official manual + community experience |
| Confidence | high |
| Residual risk | None. |

### REC-04 Foundation-model (NEP89) fine-tuning

**Goal.** Fine-tune a general foundation model (NEP89) to obtain a
high-precision potential for a specific system (interface, alloy) at low cost.

**Applicability.** Any material, interface, or defect system within the 89
supported elements.

**Inputs.** `nep89_*.txt`, `nep.restart` (shipped with NEP89), `train.xyz`,
`nep.in`.

**`nep.in` snippet.**
```text
type 5 C H O N S      # adjust to your system
# structural parameters must exactly match NEP89
cutoff 8 4
n_max 8 8
l_max 4 2 0
basis_size 12 12
neuron 100
# training parameters
batch 1000
generation 10000
fine_tune 1          # enable fine-tune
```

**Key parameters.** `fine_tune 1` plus network-architecture parameters
(`cutoff`, `neuron`, `n_max`, `l_max`, `basis_size`) that must **not** be
changed.

**Steps.**
1. Use NEP89 to run MD (NPT or high-temperature NVT) to sample `dump.xyz`.
2. Use FPS to extract representative configurations and compute DFT
   single-points.
3. Place the energy-shifted `train.xyz` and NEP89's `nep.restart` in the same
   directory and run training with `fine_tune`.

**Outputs.** Updated `nep.txt`, `loss.out`.

**Sanity check.** Step-0 loss should not be very large; within tens to
hundreds of steps the error should drop rapidly to a very low level.

**Common errors.** Changing `cutoff` or other structural parameters ->
`core dumped`; single-point energies not shifted to the NEP89 reference ->
loss diverges.

**Community warning.** Fine-tune steps should not be too long (recommended
10000-20000); longer runs cause catastrophic forgetting of the foundation
model. For a second-stage continuation after fine-tune, **remove**
`fine_tune 1` and switch to an ordinary `nep.restart` continuation.

| Field | Value |
|---|---|
| Source type | official manual + community experience |
| Confidence | high |
| Residual risk | Energy reference, element ordering, or restart incompatibility can silently invalidate the fine-tune lineage. |

### REC-05 GPUMD uniaxial tensile deformation

**Goal.** Apply continuous uniaxial strain to observe the stress-strain
response or yielding behavior.

**Applicability.** Solids, crystals, amorphous alloys, polymers.

**Inputs.** `model.xyz`, `run.in`, `nep.txt`.

**`run.in` snippet.**
```text
potential nep.txt
velocity 300
time_step 1
# 1. NPT equilibrate to zero stress
ensemble npt_scr 300 300 1000 0 0 0 100 100 100 2000
run 100000

# 2. Switch to NVT and apply deformation
ensemble nvt_bdp 300 300 100
dump_thermo 1000
# stretch along x to 15% length
deform lxx 1 0 0
run 1000000
```

**Key parameters.** `npt_scr` / `npt_ber` for equilibration; `deform` for
continuous tensile / compressive strain.

**Steps.**
1. Under NPT, allow all orthogonal directions to relax to a zero-stress state.
2. Switch to NVT (or pressure-control only on non-strain directions) to avoid
   conflict between the barostat and the deformation command.
3. Use `deform` to apply a linearly time-varying strain along the chosen
   direction; output `thermo.out` to track the diagonal stress tensor.

**Outputs.** `thermo.out` (cell lengths and stress tensor), `movie.xyz`.

**Sanity check.** The relevant stress component grows linearly with strain at
first (elastic region), then changes slope or drops (yield / fracture).

**Common errors.** `deform` rate too large -> shock-wave-like loading with
anomalous temperature rise and physical distortion.

**Community warning.** In GPUMD, using the `deform` command directly is the
smoothest approach; the LAMMPS-style "change box, run multiple times" pattern
is unnecessary here.

| Field | Value |
|---|---|
| Source type | community experience |
| Confidence | high |
| Residual risk | None. |

### REC-06 MSD and diffusion via MD

**Goal.** Run long equilibrium MD to extract diffusion coefficients and ionic
conductivity, and study defect or ion migration.

**Applicability.** Solid electrolytes, alloy interstitial diffusion,
solutions.

**Inputs.** `model.xyz` with Group labels, `run.in`, `nep.txt`.

**`run.in` snippet.**
```text
ensemble npt_mttk temp 1000 1000 iso 0 0
# MSD: max correlation 5000 steps, group 0
compute_msd 10 5000 all_groups 0 save_every 100000
dump_thermo 1000
dump_exyz 10000
run 1000000
```

**Key parameters.** `compute_msd` sampling interval (e.g. `10`), max
correlation steps (e.g. `5000`), group setup (`group 0`).

**Steps.**
1. In `model.xyz`, assign the diffusion species (e.g. Li ions, oxygen
   vacancies) to a specific group (e.g. group 0).
2. Use an elevated-temperature thermostat (e.g. `npt_mttk` to 1000K); at low
   temperature, too few hops occur to observe diffusion.
3. Ensure total `run` is strictly greater than the product of the first two
   `compute_msd` parameters (i.e. the maximum correlation time), otherwise no
   correlation function is produced.
4. After the run, use `gpumdkit.sh -plt D` or manually fit `msd.out` linearly
   to obtain D.

**Outputs.** `msd.out`.

**Sanity check.** On a log-log plot, the long-time MSD slope should be 1
(normal diffusion regime).

**Common errors.** Simulation time too short -> noisy MSD with no linear
regime; total `run` shorter than the maximum correlation time -> error.

**Community warning.** For solid electrolytes, room-temperature hopping is
too rare. The standard practice is to compute D at multiple high temperatures
(e.g. 600K-1200K) and extrapolate to room temperature via the Arrhenius
relation.

| Field | Value |
|---|---|
| Source type | official manual + community experience |
| Confidence | high |
| Residual risk | None. |

---

## §6 GPUMD Runtime Parameters

| Parameter | File | Recommended value | Rationale | Check method | Source type | Confidence |
|---|---|---|---|---|---|---|
| `ensemble` (NVT) | `run.in` | `nvt_ber` / `nvt_lan` / `nvt_bdp` for aggressive heating or pre-equilibration far from equilibrium; `nvt_nhc` for rigorous data production once equilibrated. | Using `nvt_nhc` before equilibration fails to control temperature and can collapse the structure. | Inspect `thermo.out` for stable convergence to the target temperature. | official manual + community experience | high |
| `ensemble` (NPT) | `run.in` | `npt_ber` for pre-equilibration; `npt_scr` extremely stable and gives the correct ensemble, recommended as default; `npt_mttk` rigorous but sensitive to initial fluctuations. | Using `npt_mttk` before equilibration collapses easily. | Inspect whether pressure and volume stably fluctuate around target. | official manual + community experience | high |
| `<T_coup>` (tau_T) | `run.in` | Set to ~100x the integration time step (e.g. input `100`). | Too small (e.g. 1) -> unstable thermostat, possible division by 0; too large -> very slow temperature control. | Inspect the rate at which the temperature curve approaches the target. | official manual + community experience | high |
| `<p_coup>` (tau_P) | `run.in` | Set to ~1000x the integration time step (>=500 recommended). | Too small (e.g. tens) -> pressure calculation division-by-zero risk or violent volume oscillation and collapse. | Inspect whether cell-volume change is gradual. | official manual + community experience | high |
| `<C_hydro>` | `run.in` | Set to roughly the elastic modulus, e.g. 50-100 (GPa) for typical solids, or use the experimental value. | Extreme values slow volume convergence. | Inspect whether the steady-state density is reasonable. | official manual + community experience | high |
| `time_step` | `run.in` | Typical solids: 1-2 fs; systems with light atoms (e.g. H in water): must drop to 0.5 fs; high-temperature: reduce accordingly. | A step larger than 1/10 of the fastest vibrational period destabilizes integration, causes energy drift, and rapidly triggers Error 700. | Under NVE, inspect `thermo.out` for strict energy conservation. | official manual + community experience | high |
| Cell size / atom count | `model.xyz` | Minimum cell thickness must exceed **2x the NEP cutoff**. For multi-GPU, the longest dimension per GPU must be >= **5x the cutoff** (single-node multi-GPU only; cross-node is not supported). | Too small a cell causes self-interaction or misses long-wavelength phonons; forcing multi-GPU on a small cell errors out. | Check for `The longest direction has less than 5 times of the NEP cutoff per GPU`. | official manual + community experience | high |
| `run` (equilibration) | `run.in` | System-dependent; typical solids need tens of ps; hydrated or complex organics or phase transitions may need ns or longer. | Sampling before equilibration yields wrong physical quantities (diffusion coefficient, thermal conductivity). | Monitor energy / temperature / volume curves for a stable fluctuation plateau. | community experience | high |
| `run` (production) | `run.in` | For MSD, SDC, or thermal conductivity, total time should be **>= 10x the maximum correlation time** (typically ns to tens of ns). | Insufficient time -> noisy statistics, non-converged curves. | MSD should converge to a line on log-log; autocorrelation should decay to 0. | official manual + community experience | high |
| `dump_thermo` | `run.in` | Recommended `100` or `1000` steps. | Too small (e.g. 1) -> huge files and I/O slowdown; too large -> misses high-frequency fluctuation. | Inspect `thermo.out` size and curve smoothness. | official manual + community experience | high |
| `dump_position` / `dump_exyz` | `run.in` | For sampling: `100` or more; for routine observation: `10000` or more. | Too small -> disk full and I/O slowdown. | Inspect `movie.xyz` / `dump.xyz` size. | official manual + community experience | high |
| `dump_restart` | `run.in` | For long runs: `10000` to `100000` steps. | Without it, a crash cannot resume from a recent valid point. | Check for `restart.xyz`. | official manual + community experience | high |
| `<Fe>` (HNEMD driving force) | `compute_hnemd` | `1e-5` to `1e-4` A^-1. | Too large -> non-linear response divergence; too small -> very low signal-to-noise. | Inspect whether `kappa.out` converges smoothly. | official manual + community experience | high |
| `<correlation_steps>` | `compute_hac` | Per average phonon mean free path; typically hundreds of ps to 1 ns (e.g. `1e5` to `1e6` steps at 1 fs). | Too short -> low-frequency phonon contribution missing; too long -> large tail noise. | Heat-current autocorrelation (HAC) should fully decay to 0 within the set steps. | official manual + community experience | high |
| `<Delta_T>` | `ensemble heat_lan` | A few tens of K typically; large enough for a stable heat flux but small enough not to trigger phase transition (e.g. melting). | Too large -> structural damage; too small -> low signal-to-noise. | Plot temperature vs. coordinate; the middle-region gradient should be linear. | official manual + community experience | high |
| `<sample_interval>` | `compute_shc` | Very small, typically `1` to `5`. | Larger intervals lower the Nyquist frequency and alias / truncate high-frequency phonons. | Inspect whether the result's maximum cutoff frequency covers the system's highest vibration. | official manual + community experience | high |
| `compute_phonon` | `run.in` | Force-constant cutoff >= 2x NEP `cutoff`; perturbation displacement typically `0.01` A. | Too small a supercell -> imaginary modes or acoustic branches not tending to 0 at Gamma. | Compare phonon spectra under different supercell sizes for convergence. | official manual + community experience | high |

---

## §7 Unresolved / Disputed

Items below are explicitly unresolved. Do not promote them to guidance without
independent verification.

| ID | Issue | Current state | Physical or algorithmic rationale (if any) | Source type | Confidence |
|---|---|---|---|---|---|
| UNRES-01 | Does HNEMD for charged / ionic systems implicitly include long-range Coulomb or non-analytic corrections? | Pure empirical potentials and ordinary NEP have only short-range cutoffs (e.g. 8 A). Long-range correction requires qNEP (charge model) with kspace / PPPM. qNEP training and MD are significantly slower than standard NEP and can crash in some low-dimensional systems due to boundary setup. | Long-range electrostatics is not captured by a short-range NN cutoff; an explicit charge model + Ewald-style summation is needed. | community experience | low |
| UNRES-02 | Does `lambda_v 0` affect NPT pressure balance? | Community is divided: some users report no effect, others report severely wrong density. **Physical principle**: in a uniformly compressed one-dimensional atomic chain, symmetry forces all atom forces to 0 while the virial is non-zero; fully disabling virial training can leave the force fit perfect but the pressure prediction wrong. | Virial is the derivative of energy with respect to cell volume; without direct virial supervision, the model must rely on sparse energy data to recover pressure response, which is difficult. | community experience | medium |
| UNRES-03 | Is SCF noise from low-precision but high-throughput DFT a beneficial implicit regularization (preventing overfitting) or a "garbage in, garbage out" effect? | Community still debates. | No clear algorithmic argument either way. | community experience | low |
| UNRES-04 | When should virial labels be discarded rather than repaired or re-labeled? | No universal standard. | The right answer depends on the system and on whether DFT virials are physically meaningful (e.g. vacuum cells). | community experience | low |
| UNRES-05 | Provider-version details for missing-value sentinels and neighbor diagnostics. | Not confirmed across versions. | File-format and sentinel values are version-sensitive implementation details. | community experience | low |
| UNRES-06 | Electrostatic or charge-model commands not confirmed in the current official documentation set. | Not confirmed. | Charge-model syntax and capabilities are version-sensitive. | community experience | low |
