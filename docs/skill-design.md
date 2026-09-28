# Skill Design

SimFlow has seven Research Task Skills and five Domain Skills. Each public
Skill is a portable directory with `SKILL.md` and optional focused references.
Its frontmatter describes when the host should consider it. The body adds
scientific checks, failure modes, uncertainty boundaries, and completion
criteria. Detailed software semantics live in references read only when the
request needs them.

Task and Domain Skills can be combined freely with host-native Skills. They do
not route one another, own workflow stages, initialize project state, register
artifacts, or grant permission for real execution. Research decisions and
records remain with the user. A Skill can suggest a traceable note or figure,
but it should follow the user's existing project layout.

Only ship a helper script when it performs a concrete, independently runnable
scientific operation and writes only the requested output. The installed scripts are self-contained within each Skill and behaviorally
tested from the generated packages. A parser's success does not
prove scientific validity.

Real compute, remote writes, and scheduler submission follow the host's
permission system and the user's authorization for the concrete action.
Licensed data and credentials must not enter distribution artifacts.
