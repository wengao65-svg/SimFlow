"""Tests for the parser MCP server support boundary."""

from pathlib import Path

from mcp.servers.parsers.server import handle_check_convergence, handle_parse, PARSERS


FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def test_parser_server_exposes_only_supported_helper_parsers():
    assert set(PARSERS) == {"cp2k", "lammps", "vasp"}


def test_parser_server_blocks_qe_and_gaussian_placeholders():
    for software in ["qe", "quantum_espresso", "Quantum ESPRESSO", "quantum-espresso", " gaussian "]:
        parsed = handle_parse({"software": software, "file_path": str(FIXTURES / "pw_output_Si.out")})
        convergence = handle_check_convergence({"software": software, "file_path": str(FIXTURES / "pw_output_Si.out")})

        assert parsed["status"] == "unsupported_placeholder"
        assert convergence["status"] == "unsupported_placeholder"
