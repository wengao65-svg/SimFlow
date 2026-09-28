# Credentials and Restricted Scientific Files

Use the host's existing secret and SSH mechanisms. Do not place passwords,
tokens, private keys, key paths, or arbitrary SSH options in generated inputs,
reports, logs, or package files. Inspect a script's commands and environment
requirements before real execution, without copying secret values into notes.

VASP POTCAR files are licensed. Materialize them only from a user-owned library
into the intended calculation directory. Do not print, record, commit, package,
or redistribute their content. A report may include non-content metadata needed
to check the selected dataset and element order, but must not expose the library
path.
