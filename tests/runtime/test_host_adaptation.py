"""Tests for MCP clientInfo-based host adaptation."""

from runtime.simflow_core.host_adaptation import build_initialize_instructions, detect_host


def test_detect_host_profiles():
    assert detect_host({"name": "codex-cli"}) == "codex"
    assert detect_host({"name": "Claude Code"}) == "claude_code"
    assert detect_host({"name": "Anthropic MCP Client"}) == "claude_code"
    assert detect_host({"name": "opencode"}) == "opencode"
    assert detect_host({"name": "other-client"}) == "generic"
    assert detect_host(None) == "generic"


def test_initialize_instructions_adapt_syntax_but_preserve_invariants():
    codex = build_initialize_instructions("simflow_state", {"name": "codex"})
    claude = build_initialize_instructions("simflow_state", {"name": "claude-code"})
    opencode = build_initialize_instructions("simflow_state", {"name": "opencode"})
    generic = build_initialize_instructions("simflow_state", None)

    assert "$simflow" in codex
    assert "/simflow:simflow" in claude
    assert "skill tool" in opencode
    assert "$simflow" not in generic
    for instructions in (codex, claude, opencode, generic):
        assert "project_root" in instructions
        assert "Inspect is read-only and optional" in instructions
        assert "real recovery boundaries" in instructions
        assert "dry-run-first and approval-gated" in instructions
        assert "scientific reasoning" in instructions


def test_non_state_servers_do_not_duplicate_host_guidance():
    assert build_initialize_instructions("hpc", {"name": "codex"}) is None
