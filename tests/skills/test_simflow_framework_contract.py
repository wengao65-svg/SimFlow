"""The retired Framework Skill must not enter the public Skill Pack."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_framework_skill_is_retired():
    assert not (ROOT / "skills" / "simflow" / "SKILL.md").exists()
    assert not (ROOT / "skills" / "simflow" / "agents" / "openai.yaml").exists()
    assert not (ROOT / ".mcp.json").exists()
    assert not (ROOT / ".claude.mcp.json").exists()
