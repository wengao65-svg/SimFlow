# GPUMD Official Sources

Audit date: 2026-07-10.

Use official GPUMD documentation for file-format, command, output, and
provider-implementation claims when possible. Record the GPUMD/NEP version and
access date because training keywords and examples can change.

- Stable GPUMD documentation: https://gpumd.org/gpumd/index.html
- Stable GPUMD input files: https://gpumd.org/gpumd/input_files/index.html
- Stable GPUMD output files: https://gpumd.org/gpumd/output_files/index.html
- Stable NEP documentation: https://gpumd.org/nep/index.html
- NEP v5.5 `fine_tune` parameter and NEP89 example:
  https://gpumd.org/nep/input_parameters/fine_tune.html
- NEP v5.5 `nep.restart` semantics:
  https://gpumd.org/nep/output_files/nep_restart.html
- Development documentation: https://gpumd.org/dev/index.html
- Official GPUMD source repository: https://github.com/brucefan1983/GPUMD

Use this source priority:

1. Version-matched stable documentation.
2. Version-matched official source and bundled examples.
3. Development documentation when the user explicitly targets a development
   version.
4. Cleaned community experience, clearly labeled as non-authoritative.

The v5.5 documentation establishes foundation-model `fine_tune` as officially
supported. Its syntax and model/restart compatibility are version-sensitive
implementation details. Ordinary `nep.restart` continuation and optional
community two-step training are separate concepts.

Record the source URL, version, access date, and source-code inspection status
when a report relies on a specific command, file role, or output
interpretation.
