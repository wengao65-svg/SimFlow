# Credentials Policy

## Security Rules

1. **Host-managed storage**: SSH credentials remain in OpenSSH or a host-managed agent
2. **Never write credentials**: Not to records, reports, checkpoints, scripts, or logs
3. **Never expose in errors**: Credential values never appear in error messages
4. **Graceful fallback**: Missing optional credentials use an open connector or
   a clearly marked unverified fallback; they never fabricate verified evidence
5. **Sanitize logs**: `sanitize_for_logging()` strips potential tokens from output

## Supported Credentials

| Environment Variable | Service | Required | Purpose |
|---------------------|---------|----------|---------|
| `S2_API_KEY` | Semantic Scholar | No | Literature search |
| `SIMFLOW_VASP_POTCAR_PATH` | User-owned VASP library | No | Controlled local POTCAR materialization |
| `SIMFLOW_VASP_POTCAR_FLAVOR` | VASP dataset selection | No | Functional family such as PBE or LDA |

## Fallback Behavior

| Service | With Credentials | Without Credentials |
|---------|-----------------|---------------------|
| Semantic Scholar | Live API queries | OpenAlex; mock only as `mock_unverified` degraded fallback |
| arXiv | Always available | Public API, no key needed |
| Crossref | Always available | Public API, no key needed |
| SSH HPC | Host OpenSSH/agent authenticates approved broker operations | Remote operations fail closed |
| SLURM/PBS | Approved immutable plan may be submitted | Planning and script validation remain available |
| Local execution | Approved immutable plan may be executed | Unapproved execution remains blocked |

## Setting Credentials

```bash
# In shell profile (~/.bashrc, ~/.zshrc)
export S2_API_KEY="your-api-key-here"

# A host may load an untracked .env before starting the plugin.
# SimFlow itself reads credentials only from the process environment.
```

## API Key Acquisition

- **Semantic Scholar**: Register at semanticscholar.org → API → Generate key
- **arXiv**: No key needed (public API with rate limits)
- **Crossref**: No key needed (public API, polite pool with email)

## Log Sanitization

The `sanitize_for_logging()` function replaces token-like strings of 32 or more
characters, including common token punctuation, with `[REDACTED]`:

```python
from mcp.shared.credentials import sanitize_for_logging

safe_text = sanitize_for_logging("Using key sk-abcdefghijklmnopqrstuvwxyz1234567890")
# Returns: "Using key [REDACTED]"
```

## Best Practices

- Use project-specific API keys, not personal ones
- Rotate keys periodically
- Never commit `.env` files to version control
- Never pass SSH key paths, private-key contents, or passwords through MCP parameters
- Keep `SIMFLOW_VASP_POTCAR_PATH` out of records and reports; persist only
  materialized file metadata allowed by the POTCAR policy
- Run `scripts/start_hpc_broker.py` in the permission domain that owns SSH credentials
- Give the Agent-facing plugin only `SIMFLOW_HPC_BROKER_SOCKET`, not the broker's SSH agent socket
- Deny Agent shell access to `.ssh` and direct access to the broker socket outside MCP policy
- Use `check_all_credentials()` to verify availability without returning secret values
