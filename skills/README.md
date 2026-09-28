# SimFlow Skills

SimFlow distributes 12 independent computational-research Skills. The seven
Research Task Skills cover literature review, reference extraction, proposal,
modeling, computation, analysis and visualization, and writing. The five Domain
Skills cover VASP, CP2K, LAMMPS, GPUMD/NEP, and machine-learning potentials.

The host discovers and combines the Skills relevant to the user's task. Skills
provide scientific guidance and references; they neither maintain a SimFlow
experiment notebook nor require MCP calls, stage transitions, registrations,
or checkpoints. The user owns scientific decisions and records. An agent can
help draft a note in the user's chosen location.

Each installed Skill includes its standalone scripts and local `lib/` or
`assets/` resources where needed. Pure checks print JSON; reports are written
only to an explicitly requested path. Real execution follows the host's permissions and the user's authorization for the concrete action.
