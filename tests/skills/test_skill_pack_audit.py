"""Public Skill scripts do not depend on retired project state."""

from pathlib import Path

from scripts.audit_skill_pack import audit


ROOT = Path(__file__).resolve().parents[2]


def test_skill_pack_audit_finds_twelve_clean_skills():
    report = audit()
    assert report["current_skill_count"] == 12
    assert len(report["skills"]) == 12
    for skill in report["skills"]:
        assert not skill.get("frontmatter_error")
        assert not skill.get("state_terms")
        assert not skill.get("runtime_scripts")


def test_retired_state_sources_and_entrypoints_are_absent():
    for name in ("runtime", "mcp", "workflow", "schemas"):
        assert not (ROOT / name).exists()
    for name in ("start_mcp_server.py", "start_hpc_broker.py", "scaffold_stage.js"):
        assert not (ROOT / "scripts" / name).exists()


def test_public_python_helpers_do_not_import_retired_namespaces():
    for path in (ROOT / "skills").glob("*/**/*.py"):
        source = path.read_text(encoding="utf-8")
        assert "from runtime." not in source
        assert "from mcp." not in source
        assert "record_helper_run" not in source
