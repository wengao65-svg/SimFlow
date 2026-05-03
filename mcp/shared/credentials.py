"""Credential management for SimFlow MCP connectors.

Security rules:
- Credentials are read ONLY from environment variables
- Never write credentials to files, artifacts, logs, or state
- Never include credentials in error messages
- Graceful fallback to dry-run/mock when credentials are missing
"""

import os
from typing import Optional


# Known credential environment variables
CREDENTIAL_ENV_VARS = {
    "MP_API_KEY": {
        "service": "Materials Project",
        "required": False,
        "description": "Materials Project API key for structure database access",
    },
    "S2_API_KEY": {
        "service": "Semantic Scholar",
        "required": False,
        "description": "Semantic Scholar API key for literature search",
    },
    "SIMFLOW_SSH_HOST": {
        "service": "SSH HPC",
        "required": False,
        "description": "SSH host for remote job submission",
    },
    "SIMFLOW_SSH_USER": {
        "service": "SSH HPC",
        "required": False,
        "description": "SSH username",
    },
    "SIMFLOW_SSH_KEY": {
        "service": "SSH HPC",
        "required": False,
        "description": "Path to SSH private key file",
    },
}


def get_api_key(service: str) -> Optional[str]:
    """Get API key for a service from environment variables.

    Args:
        service: Service name (e.g., 'materials_project', 'semantic_scholar')

    Returns:
        API key string or None if not set
    """
    env_map = {
        "materials_project": "MP_API_KEY",
        "semantic_scholar": "S2_API_KEY",
    }
    env_var = env_map.get(service)
    if env_var:
        return os.environ.get(env_var)
    return None


def require_api_key(service: str) -> str:
    """Get API key or raise if not set.

    Args:
        service: Service name

    Returns:
        API key string

    Raises:
        RuntimeError: If API key is not set
    """
    key = get_api_key(service)
    if not key:
        env_map = {
            "materials_project": "MP_API_KEY",
            "semantic_scholar": "S2_API_KEY",
        }
        env_var = env_map.get(service, "UNKNOWN_API_KEY")
        raise RuntimeError(
            "API key for {} not found. Set {} environment variable.".format(service, env_var)
        )
    return key


def check_ssh_credentials() -> dict:
    """Check SSH credentials availability.

    Returns:
        Dict with host, user, key_file availability
    """
    return {
        "host": bool(os.environ.get("SIMFLOW_SSH_HOST")),
        "user": bool(os.environ.get("SIMFLOW_SSH_USER")),
        "key_file": bool(os.environ.get("SIMFLOW_SSH_KEY")),
        "ready": bool(os.environ.get("SIMFLOW_SSH_HOST")),
    }


def check_all_credentials() -> dict:
    """Check all known credentials.

    Returns:
        Dict mapping service names to availability status
    """
    result = {}
    for env_var, info in CREDENTIAL_ENV_VARS.items():
        result[info["service"]] = {
            "available": bool(os.environ.get(env_var)),
            "env_var": env_var,
            "required": info["required"],
        }
    return result


def sanitize_for_logging(text: str) -> str:
    """Remove any potential credentials from text before logging.

    Simple pattern: replace any string that looks like an API key.
    """
    import re
    # Remove anything that looks like a long alphanumeric token
    sanitized = re.sub(r'[A-Za-z0-9]{32,}', '[REDACTED]', text)
    return sanitized
