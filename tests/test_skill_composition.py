"""The host can compose Task and Domain Skills without a central router."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_skill_pack_has_no_framework_router():
    assert not (ROOT / "skills" / "simflow" / "SKILL.md").exists()
    assert not (ROOT / "skills" / "simflow" / "router_contract.json").exists()


def test_documented_composition_keeps_user_in_control():
    readme = (ROOT / "skills" / "README.md").read_text(encoding="utf-8").lower()
    assert "host discovers and combines" in readme
    assert "user owns scientific decisions and records" in readme
    assert "real execution follows the host's permissions" in readme
