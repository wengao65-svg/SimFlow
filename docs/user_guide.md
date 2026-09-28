# Using SimFlow Skills

Start with a concrete scientific request: a research question, existing inputs,
output files, or a draft. The host agent discovers the relevant Research Task
and Domain Skills. For example, a VASP relaxation review can combine modeling,
computation, and VASP guidance; a GPUMD potential assessment can combine
computation, GPUMD, MLP, and analysis guidance.

The agent should inspect the user's actual files and explain what is known,
unknown, or inconsistent. A proposed change to a validated scientific
parameter needs a reason and visible diff. A scheduler job ID only shows
submission; output files need convergence and scientific checks before a result
is reported as usable.

Use the project's existing README, experiment notebook, Git history, or chosen
record location for continuity. Ask the agent to draft a note there if useful.
SimFlow Skills do not create their own experiment ledger, stage state, artifact
registry, or `.simflow/` directory. Existing `.simflow/` data remains untouched.

For real local compute, remote writes, or scheduler submission, review the
concrete command, inputs, destination, resources, cost, and overwrite scope.
The host's permissions and the user's authorization control execution. A
materially changed action may need renewed authorization. Credentials and
licensed POTCAR content must stay out of logs, reports, responses, and packages.

Each installed Skill includes its optional scripts and local resources. Pure
checks print JSON by default; use an explicit report path when a durable file
is useful. Use the project's existing research notebook for experiment records.
