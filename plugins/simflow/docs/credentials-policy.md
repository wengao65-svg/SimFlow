# Credentials Policy

## Security Rules

1. **Host-managed storage**: SSH credentials remain in OpenSSH or a host-managed agent
2. **Never write credentials**: Not to files, artifacts, logs, or state
3. **Never expose in errors**: Credential values never appear in error messages
4. **Graceful fallback**: Missing optional credentials use an open connector or
   a clearly marked unverified fallback; they never fabricate verified evidence
5. **Sanitize logs**: `sanitize_for_logging()` strips potential tokens from output

## Supported Credentials

| Environment Variable | Service | Required | Purpose |
|---------------------|---------|----------|---------|
| `MP_API_KEY` | Materials Project | No | Structure database access |
| `S2_API_KEY` | Semantic Scholar | No | Literature search |

## Fallback Behavior

| Service | With Credentials | Without Credentials |
|---------|-----------------|---------------------|
| Materials Project | Live API queries | Mock connector (sample data) |
| Semantic Scholar | Live API queries | OpenAlex; mock only as `mock_unverified` degraded fallback |
| arXiv | Always available | Public API, no key needed |
| Crossref | Always available | Public API, no key needed |
| COD | Always available | Public API, no key needed |
| SSH HPC | Host OpenSSH/agent authenticates approved MCP operations | Remote operations fail |
| SLURM | Direct submission | Script generation only |
| Local | Always available | Subprocess execution |

## Setting Credentials

```bash
# In shell profile (~/.bashrc, ~/.zshrc)
export MP_API_KEY="your-api-key-here"
export S2_API_KEY="your-api-key-here"

# Or in .env file (NOT committed to version control)
# .env is automatically loaded if present
```

## API Key Acquisition

- **Materials Project**: Register at materialsproject.org → API → Generate key
- **Semantic Scholar**: Register at semanticscholar.org → API → Generate key
- **arXiv**: No key needed (public API with rate limits)
- **Crossref**: No key needed (public API, polite pool with email)

## Log Sanitization

The `sanitize_for_logging()` function replaces any alphanumeric string longer than 32 characters with `[REDACTED]`:

```python
from mcp.shared.credentials import sanitize_for_logging

safe_text = sanitize_for_logging("Using key ABC123...longtoken...XYZ")
# Returns: "Using key [REDACTED]"
```

## Best Practices

- Use project-specific API keys, not personal ones
- Rotate keys periodically
- Never commit `.env` files to version control
- Never pass SSH key paths, private-key contents, or passwords through MCP parameters
- Run `scripts/start_hpc_broker.py` in the permission domain that owns SSH credentials
- Give the Agent-facing plugin only `SIMFLOW_HPC_BROKER_SOCKET`, not the broker's SSH agent socket
- Deny Agent shell access to `.ssh` and direct access to the broker socket outside MCP policy
- Use `check_all_credentials()` to verify setup before running workflows
