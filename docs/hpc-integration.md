# HPC and Real Execution

SimFlow ships no HPC MCP, scheduler connector, credential broker, or submission
state machine. `simflow-computation` guides input and job-script review;
`prepare_job.py` creates Slurm or PBS script text in a named destination but
never submits it.

Before real local compute, transfer, remote write, or scheduler submission,
review the exact command and script, input files, destination, resources, cost,
and any overwrite or destructive scope. Follow the host's permission mechanism
and the user's authorization for that concrete action. If the action materially
changes, reassess the authorization. The host may use the user's existing
scheduler and SSH tools; SimFlow does not record approval hashes.

Keep credentials and private key paths out of scripts, reports, and responses.
A scheduler job ID confirms submission only. Check scheduler status and the
scientific outputs separately before claiming completion or convergence.
