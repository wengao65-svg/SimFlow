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
    "SIMFLOW_VASP_POTCAR_PATH": {
        "service": "VASP POTCAR",
        "required": False,
        "description": "Path to VASP pseudopotential library (potpaw, potpaw_PBE, etc.)",
    },
    "SIMFLOW_VASP_POTCAR_FLAVOR": {
        "service": "VASP POTCAR",
        "required": False,
        "description": "POTCAR functional type: PBE (default), LDA, PW91",
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


def check_potcar_config() -> dict:
    """Check VASP POTCAR configuration.

    Returns:
        Dict with potcar_path, flavor, path_exists, and generation method
    """
    import shutil
    potcar_path = os.environ.get("SIMFLOW_VASP_POTCAR_PATH")
    flavor = os.environ.get("SIMFLOW_VASP_POTCAR_FLAVOR", "PBE")
    path_exists = os.path.isdir(potcar_path) if potcar_path else False
    vaspkit = shutil.which("vaspkit") is not None

    method = None
    if path_exists:
        method = "concatenation"
    elif vaspkit:
        method = "vaspkit"

    return {
        "potcar_path": potcar_path,
        "flavor": flavor,
        "path_exists": path_exists,
        "vaspkit_available": vaspkit,
        "method": method,
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
