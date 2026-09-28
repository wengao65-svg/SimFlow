#!/usr/bin/env python3
"""Audit the public Skill surface without touching project state.

This is a migration aid, not a workflow gate.  It reports references that
must be removed before the runtime can be retired and exits non-zero only with
``--strict``.  The default mode is useful in CI and for a human audit because
it never creates ``.simflow`` files or rewrites the repository.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILLS_ROOT = ROOT / "skills"
PUBLIC_EXCLUSIONS = {"simflow"}
FRONTMATTER_RE = re.compile(r"\A---\n(?P<body>.*?)\n---(?:\n|\Z)", re.DOTALL)
STATE_TERMS = (
    ".simflow",
    "run_plan_hash",
    "record_helper_run",
    "simflow_state",
    "runtime.simflow",
)


def parse_frontmatter(path: Path) -> tuple[dict[str, str], str | None]:
    text = path.read_text(encoding="utf-8")
    match = FRONTMATTER_RE.match(text)
    if not match:
        return {}, "missing standalone YAML frontmatter"
    fields: dict[str, str] = {}
    for line in match.group("body").splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            fields[key.strip()] = value.strip()
    missing = [key for key in ("name", "description") if not fields.get(key)]
    return fields, f"missing {', '.join(missing)}" if missing else None


def audit() -> dict[str, object]:
    skills: list[dict[str, object]] = []
    for skill_dir in sorted(SKILLS_ROOT.iterdir()):
        if not skill_dir.is_dir() or skill_dir.name in PUBLIC_EXCLUSIONS:
            continue
        skill_file = skill_dir / "SKILL.md"
        if not skill_file.is_file():
            skills.append({"skill": skill_dir.name, "error": "missing SKILL.md"})
            continue
        fields, error = parse_frontmatter(skill_file)
        if error is None and fields.get("name") != skill_dir.name:
            error = "frontmatter name differs from directory"
        body = skill_file.read_text(encoding="utf-8").lower()
        findings = [term for term in STATE_TERMS if term in body]
        script_imports: list[str] = []
        for script in sorted(skill_dir.rglob("*.py")):
            script_text = script.read_text(encoding="utf-8")
            if "runtime." in script_text or "mcp." in script_text:
                script_imports.append(str(script.relative_to(ROOT)))
        entry: dict[str, object] = {
            "skill": skill_dir.name,
            "name": fields.get("name"),
            "frontmatter_error": error,
            "state_terms": findings,
            "runtime_scripts": script_imports,
        }
        skills.append(entry)
    current_count = len(list(SKILLS_ROOT.glob("*/SKILL.md")))
    return {
        "current_skill_count": current_count,
        "target_skill_count": len(skills),
        "skills": skills,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="print machine-readable output")
    parser.add_argument("--strict", action="store_true", help="fail when migration findings exist")
    args = parser.parse_args()
    report = audit()
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"Current Skills: {report['current_skill_count']}; target Task/Domain Skills: {report['target_skill_count']}")
        for item in report["skills"]:
            assert isinstance(item, dict)
            problems = []
            if item.get("frontmatter_error"):
                problems.append(str(item["frontmatter_error"]))
            if item.get("state_terms"):
                problems.append("state terms: " + ", ".join(item["state_terms"]))
            if item.get("runtime_scripts"):
                problems.append(f"runtime-dependent scripts: {len(item['runtime_scripts'])}")
            print(f"- {item['skill']}: " + ("; ".join(problems) if problems else "ready"))
    if args.strict:
        for item in report["skills"]:
            assert isinstance(item, dict)
            if item.get("frontmatter_error") or item.get("state_terms") or item.get("runtime_scripts"):
                return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
