"""Static checks for SimFlow scaffold templates."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_skill_scaffold_generates_frontmatter_and_pure_guidance_sections():
    text = (ROOT / "scripts" / "scaffold_skill.js").read_text(encoding="utf-8")

    assert "const template = `---" in text
    assert "name: ${name}" in text
    assert "description: ${description" in text
    assert "## Minimum checks" in text
    assert "## Common failure modes" in text
    assert "user's authorization" in text
    assert "does not create project state" in text
