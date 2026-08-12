# Silicon Band-Structure Input Example

This directory contains redistributable VASP input metadata for relaxation,
SCF, and band-structure preparation. Validate it without licensed POTCAR
content or real execution:

```bash
python examples/si_band_structure/validate_inputs.py
```

The example does not provide a direct SSH, SCP, scheduler, or VASP execution
script. For a real calculation, materialize the licensed POTCAR in the
controlled calculation directory, create an immutable `hpc/plan` for the exact
script and inputs, obtain approval bound to its `run_plan_hash`, and use the
public `hpc/transfer`, `hpc/submit`, and `hpc/status` tools.
