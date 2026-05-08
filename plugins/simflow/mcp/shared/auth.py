"""Credential reading and permission checks.

Credentials are read from environment variables only.
Never stored in repository, artifacts, or logs.
"""

import os
from typing import Optional

from .errors import AuthError


def get_api_key(service: str) -> Optional[str]:
    """Get API key for a service from environment variables.

    Args:
        service: Service name (e.g., 'materials_project', 'crossref', 'semantic_scholar')

    Returns:
        API key string, or None if not set
    """
    env_var = f"SIMFLOW_{service.upper()}_API_KEY"
    return os.environ.get(env_var)


def require_api_key(service: str) -> str:
    """Get API key or raise AuthError.

    Args:
        service: Service name

    Returns:
        API key string

    Raises:
        AuthError: If API key is not set
    """
    key = get_api_key(service)
    if not key:
        env_var = f"SIMFLOW_{service.upper()}_API_KEY"
        raise AuthError(
            f"API key for '{service}' not found. "
            f"Set environment variable {env_var}"
        )
    return key


def check_ssh_access() -> bool:
    """Check if SSH access is available."""
    ssh_key = os.path.expanduser("~/.ssh/id_rsa")
    return os.path.exists(ssh_key)


def check_hpc_submit_allowed() -> bool:
    """Check if HPC job submission is allowed.

    Returns False by default for safety. Must be explicitly enabled.
    """
    return os.environ.get("SIMFLOW_ALLOW_HPC_SUBMIT", "").lower() in ("true", "1", "yes")
