# Credentials Policy

## Security Rules

1. **Environment-only storage**: Credentials are read ONLY from environment variables
2. **Never write credentials**: Not to files, artifacts, logs, or state
3. **Never expose in errors**: Credential values never appear in error messages
4. **Graceful fallback**: Missing credentials trigger dry-run/mock mode
5. **Sanitize logs**: `sanitize_for_logging()` strips potential tokens from output

## Supported Credentials

| Environment Variable | Service | Required | Purpose |
|---------------------|---------|----------|---------|
| `MP_API_KEY` | Materials Project | No | Structure database access |
| `S2_API_KEY` | Semantic Scholar | No | Literature search |
| `SIMFLOW_SSH_HOST` | SSH HPC | No | Remote job submission host |
| `SIMFLOW_SSH_USER` | SSH HPC | No | SSH username |
| `SIMFLOW_SSH_KEY` | SSH HPC | No | SSH private key file path |

## Fallback Behavior

| Service | With Credentials | Without Credentials |
|---------|-----------------|---------------------|
| Materials Project | Live API queries | Mock connector (sample data) |
| Semantic Scholar | Live API queries | Mock connector (sample data) |
| arXiv | Always available | Public API, no key needed |
| Crossref | Always available | Public API, no key needed |
| COD | Always available | Public API, no key needed |
| SSH HPC | Remote execution | Dry-run validation only |
| SLURM | Direct submission | Script generation only |
| Local | Always available | Subprocess execution |

## Setting Credentials

```bash
# In shell profile (~/.bashrc, ~/.zshrc)
export MP_API_KEY="your-api-key-here"
export S2_API_KEY="your-api-key-here"
export SIMFLOW_SSH_HOST="hpc.university.edu"
export SIMFLOW_SSH_USER="researcher"
export SIMFLOW_SSH_KEY="$HOME/.ssh/hpc_key"

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
- Use `check_all_credentials()` to verify setup before running workflows
