"""Contract tests for the generic MLP and GPUMD/NEP skill boundary."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MLP_SKILL = ROOT / "skills" / "simflow-mlp"
GPUMD_SKILL = ROOT / "skills" / "simflow-gpumd"
COMMUNITY_REFERENCE = GPUMD_SKILL / "references" / "gpumd_nep_community_methodology.md"
CAPABILITIES = ROOT / "workflow" / "toolchains" / "capabilities.json"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _all_markdown(root: Path) -> str:
    return "\n".join(_read(path) for path in sorted(root.rglob("*.md")))


def test_mlp_uses_provider_defined_training_policy():
    skill = _read(MLP_SKILL / "SKILL.md")
    training = _read(MLP_SKILL / "references" / "mlp_training_validation.md")
    combined = f"{skill}\n{training}"

    for phrase in [
        "Provider-defined training policy",
        "from-scratch",
        "restart",
        "fine-tuning",
        "multi-task",
        "optimizer",
        "scheduler",
        "checkpoint lineage",
        "stopping conditions",
    ]:
        assert phrase.lower() in combined.lower(), phrase

    assert "does not prescribe a provider-independent training-phase sequence" in combined


def test_nep_two_step_training_is_not_generic_mlp_methodology():
    mlp_text = _all_markdown(MLP_SKILL)

    assert not re.search(
        r"\b(?:(?:two[- ]step|two[- ]stage)[- ]training|staged[- ]training)\b",
        mlp_text,
        re.IGNORECASE,
    )
    for prescription in [
        r"\b(?:all|every)\s+(?:MLP|model|trainer)s?.{0,80}\b(?:(?:two[- ]step|two[- ]stage)[- ]training|staged[- ]training)\b",
        r"\b(?:must|should|required to)\s+(?:use|adopt|follow)\s+(?:a\s+)?(?:(?:two[- ]step|two[- ]stage)[- ]training|staged[- ]training)\b",
    ]:
        assert not re.search(prescription, mlp_text, re.IGNORECASE | re.DOTALL)

    community = _read(COMMUNITY_REFERENCE)
    assert "NEP optional two-step training" in community
    for label in [
        "community-derived",
        "NEP-specific",
        "optional",
        "version-sensitive implementation",
    ]:
        assert label in community


def test_gpumd_distinguishes_fine_tune_restart_and_community_strategy():
    evidence = _read(GPUMD_SKILL / "references" / "gpumd_nep_evidence.md")
    community = _read(COMMUNITY_REFERENCE)
    combined = f"{evidence}\n{community}"

    for phrase in [
        "foundation-model fine-tuning",
        "fine_tune <nep_model_file> <nep_restart_file>",
        "officially-supported",
        "ordinary checkpoint/restart",
        "nep.restart",
        "community two-step training",
    ]:
        assert phrase.lower() in combined.lower(), phrase

    assert "version-sensitive implementation" in combined


def test_gpumd_file_map_covers_generic_mlp_evidence_roles():
    file_map = _read(GPUMD_SKILL / "references" / "gpumd_file_map.md")

    expected_mappings = {
        "`train.xyz` / `test.xyz`": "dataset evidence",
        "`nep.in`": "trainer configuration",
        "`loss.out`": "training metrics",
        "`nep.restart`": "checkpoint/restart lineage",
        "`nep.txt`": "model artifact",
        "`run.in` / `model.xyz`": "MD validation inputs",
        "`thermo.out`": "MD stability evidence",
        "`neighbor.out`": "runtime/structural diagnostic evidence",
        "active-learning candidate structures": "candidate-pool evidence",
    }
    for artifact, role in expected_mappings.items():
        assert artifact in file_map
        assert role in file_map

    assert "target-property evidence" in file_map


def test_gpumd_owns_provider_files_and_delegates_generic_readiness():
    text = _read(GPUMD_SKILL / "SKILL.md")

    for filename in [
        "train.xyz",
        "test.xyz",
        "nep.in",
        "loss.out",
        "nep.restart",
        "nep.txt",
        "run.in",
        "model.xyz",
        "thermo.out",
        "neighbor.out",
    ]:
        assert filename in text

    assert "simflow-mlp" in text
    assert "does not redefine general MLP production-readiness criteria" in text
    assert "troubleshooting" in text.lower()


def test_vasp_mlp_and_gpumd_use_domain_assistant_product_terminology():
    for skill_name in ["simflow-vasp", "simflow-mlp", "simflow-gpumd"]:
        text = _read(ROOT / "skills" / skill_name / "SKILL.md").lower()
        assert "domain assistant" in text, skill_name

    positioning = "\n".join(
        _read(path)
        for path in [
            ROOT / "README.md",
            ROOT / "skills" / "README.md",
            ROOT / "docs" / "skill-design.md",
            ROOT / "docs" / "software-skills.md",
        ]
    )
    assert "Domain Assistants" in positioning
    for stale_term in [
        "Domain Helpers",
        "general MLP evidence helper",
        "Cross-tool domain helpers such as `simflow-mlp`",
        "cross-tool evidence helper for machine-learning-potential",
        "Engine helpers should answer questions such as:",
    ]:
        assert stale_term not in positioning


def test_domain_assistant_helper_support_and_helper_evidence_are_separate_concepts():
    contract = json.loads(_read(CAPABILITIES))
    policy = contract["policy"].lower()

    assert "domain assistant" in policy
    assert "helper support" in policy
    assert "helper-evidence" in policy
    assert {"gpumd", "nep"} <= set(contract["helper_supported_software"])
    for tool in ["gpumd", "nep"]:
        supported = set(contract["capability_support"][tool]["supported"])
        assert {
            "input_generation",
            "input_validation",
            "compute_planning",
            "orchestration",
            "static_input_inspection",
            "manifest_generation",
            "selected_output_parsing",
            "evidence_handoff",
        } <= supported


def test_community_reference_is_cleaned_anonymized_and_version_separated():
    text = _read(COMMUNITY_REFERENCE)

    for phrase in [
        "Source:",
        "Untracked local community material under",
        ".simflow/community-gpumd-nep/",
        "Status:",
        "Community-derived, cleaned and checked",
        "Not authoritative:",
        "Stable methodology",
        "Version-sensitive notes",
        "Official-document consistency:",
        "Source-code consistency:",
        "Residual risk:",
        "Recommended use:",
    ]:
        assert phrase in text

    assert not re.search(r"\b1[3-9]\d{9}\b", text)
    assert not re.search(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", text, re.IGNORECASE)
    assert not re.search(r"\b(?:QQ|qq)\s*[:：]?\s*\d{5,12}\b", text)
    for private_marker in ["QQ号", "微信号", "联系方式", "私人项目"]:
        assert private_marker not in text

    assert "### Target-scale and target-property evidence" not in text
    assert "General dataset, labeling, validation, active-learning, and production-MD" in text


def test_skill_reference_maps_resolve():
    for skill_dir in [MLP_SKILL, GPUMD_SKILL]:
        skill_text = _read(skill_dir / "SKILL.md")
        references = re.findall(r"`references/([^`]+\.md)`", skill_text)
        assert references, skill_dir.name
        for reference in references:
            assert (skill_dir / "references" / reference).is_file(), reference


def test_raw_community_material_is_not_git_tracked():
    tracked = subprocess.run(
        ["git", "ls-files", ".simflow/community-gpumd-nep"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert tracked.stdout.strip() == ""
    assert ".simflow/" in _read(ROOT / ".gitignore")

    raw_dir = ROOT / ".simflow" / "community-gpumd-nep"
    if raw_dir.is_dir():
        raw_files = sorted(raw_dir.glob("*.txt"))
        assert raw_files
        for raw_file in raw_files:
            ignored = subprocess.run(
                ["git", "check-ignore", "-q", str(raw_file.relative_to(ROOT))],
                cwd=ROOT,
                check=False,
            )
            assert ignored.returncode == 0, raw_file.name
