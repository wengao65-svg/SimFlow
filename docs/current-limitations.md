# Current Product Limitations

SimFlow ships 12 Research Task and Domain Skills, with optional standalone
scientific scripts. They provide guidance and focused checks; they do not
manage experiments, guarantee scientific validity, or submit jobs.

The former `runtime.*` and `mcp.*` Python APIs and their stateful commands have
been removed. Existing projects that imported them need to move to the
appropriate Skill script or their own project tooling. Existing `.simflow/`
user data is not converted by this release.

Scripts need the relevant Python libraries in the user's environment. VASP, GPUMD/NEP, and structure generation use `pymatgen`; CP2K CIF conversion
and LAMMPS structure conversion use ASE. Analysis tools may need plotting or
trajectory libraries. See [helper dependencies](helper-dependencies.md). Their checks cover selected file fields
and common cases, not all software versions or scientific workflows. Consult
the engine documentation and inspect original outputs for consequential claims.

Real local, remote, or scheduler execution uses the host's permissions and the
user's authorization for the concrete action. A Skill cannot mechanically
intercept arbitrary shell commands. A job ID, output file, or successful parser
run does not establish convergence. Existing `.simflow/` directories are
historical user data and are left untouched.

Licensed POTCAR content and credentials must stay out of responses, reports,
commits, and packages. The VASP helper can materialize POTCAR only from a
user-owned library into a controlled calculation directory.

The VASP lightweight parser does not infer convergence from OSZICAR, minimal
XML extraction, or EIGENVAL. These sources provide data only. OUTCAR checks
separate final SCF evidence, structural stopping evidence, and normal
termination. The output validator's force threshold is an additional requested
check; it is not a substitute for the calculation's original convergence criteria.
CP2K CIF conversion expands symmetry using ASE and rejects partial/disordered
occupancies; resolve those structures explicitly before generating inputs.
