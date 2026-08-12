"""Credential metadata and log-redaction behavior."""

from mcp.shared.credentials import CREDENTIAL_ENV_VARS, get_api_key, sanitize_for_logging


def test_only_implemented_api_credentials_are_advertised(monkeypatch):
    assert "MP_API_KEY" not in CREDENTIAL_ENV_VARS
    assert "S2_API_KEY" in CREDENTIAL_ENV_VARS
    monkeypatch.setenv("S2_API_KEY", "semantic-key")
    assert get_api_key("semantic_scholar") == "semantic-key"
    assert get_api_key("materials_project") is None


def test_log_sanitizer_redacts_token_punctuation():
    token = "sk-abcdefghijklmnopqrstuvwxyz1234567890"
    assert sanitize_for_logging(f"Using key {token}") == "Using key [REDACTED]"


def test_log_sanitizer_preserves_short_identifiers():
    assert sanitize_for_logging("job_id=slurm_12345") == "job_id=slurm_12345"
