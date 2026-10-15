"""Specification and documentation tests for the ProDoc Guard skill itself.

These tests encode the Agent Skills rules from
https://agentskills.io/specification and check this repository's own artefacts:
SKILL.md frontmatter, progressive-disclosure budgets, bundled-file references,
template/section agreement, and the documentation the release depends on.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from support import CHECK_SKILL, CLI, REPO_ROOT, TEMPLATES, load_prodoc  # noqa: E402

SKILL_MD = REPO_ROOT / "SKILL.md"
SPEC_FIELDS = {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}


def run(cmd, cwd=REPO_ROOT):
    return subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, timeout=120)


class SkillFrontmatterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.prodoc = load_prodoc()
        cls.text = SKILL_MD.read_text(encoding="utf-8")
        cls.data, _warnings = cls.prodoc.load_frontmatter(cls.text)

    def test_frontmatter_parses_as_a_mapping(self):
        self.assertIsInstance(self.data, dict)

    def test_name_is_required_and_matches_the_directory(self):
        self.assertEqual(self.data["name"], REPO_ROOT.name)
        self.assertRegex(self.data["name"], r"^[a-z0-9]+(-[a-z0-9]+)*$")
        self.assertLessEqual(len(self.data["name"]), 64)

    def test_description_length_and_trigger_keywords(self):
        description = self.data["description"]
        self.assertTrue(description.strip())
        self.assertLessEqual(len(description), 1024)
        lowered = description.lower()
        for keyword in ("prodoc-guard", "documentation", "git", "decision", "status"):
            self.assertIn(keyword, lowered, "description should mention %r" % keyword)
        self.assertIn("use when", lowered)

    def test_compatibility_is_present_and_within_limits(self):
        self.assertIn("compatibility", self.data)
        self.assertLessEqual(len(self.data["compatibility"]), 500)
        self.assertIn("git", self.data["compatibility"].lower())

    def test_only_specification_fields_are_used(self):
        unknown = set(self.data) - SPEC_FIELDS
        self.assertEqual(unknown, set(), "unexpected frontmatter fields: %s" % unknown)

    def test_experimental_allowed_tools_is_not_used(self):
        self.assertNotIn("allowed-tools", self.data)

    def test_metadata_values_are_strings(self):
        metadata = self.data.get("metadata")
        self.assertIsInstance(metadata, dict)
        for key, value in metadata.items():
            self.assertIsInstance(value, str, "metadata.%s must be a string" % key)

    def test_license_field_points_at_a_bundled_licence(self):
        self.assertIn("MIT", self.data["license"])
        self.assertTrue((REPO_ROOT / "LICENSE").is_file())

    def test_progressive_disclosure_budget(self):
        lines = self.text.splitlines()
        self.assertLess(len(lines), 500, "SKILL.md body should stay under 500 lines")
        words = len(self.prodoc.strip_comments(self.text).split())
        self.assertLess(words, 5000, "SKILL.md should stay under 5000 tokens")

    def test_bundled_references_all_exist(self):
        missing = [
            reference
            for reference in self.prodoc.referenced_bundled_files(self.text)
            if not (REPO_ROOT / reference).exists()
        ]
        self.assertEqual(missing, [])

    def test_skill_names_the_three_canonical_documents(self):
        for doc in ("PRODUCT_REQUIREMENTS.md", "DECISION_LOG.md", "PROJECT_STATUS.md"):
            self.assertIn(doc, self.text)

    def test_skill_states_the_work_state_vocabulary(self):
        for state in ("Planned", "Implemented", "Tested", "Deployed", "Published", "Blocked"):
            self.assertIn(state, self.text)

    def test_skill_requires_evidence_and_authorization(self):
        lowered = self.text.lower()
        for phrase in ("never claim", "evidence", "authoriz", "read all three"):
            self.assertIn(phrase, lowered)

    def test_skill_documents_that_documents_are_data_not_instructions(self):
        lowered = self.text.lower()
        self.assertTrue(
            "not instructions" in lowered or "data, not instructions" in lowered,
            "SKILL.md must state that documentation is data, not instructions",
        )


class CheckSkillScriptTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.prodoc = load_prodoc()

    def make_skill(self, tmp, name="good-skill", body=None, description=None):
        directory = Path(tmp) / name
        directory.mkdir(parents=True)
        description = description or "Does a thing. Use when a thing needs doing in a project."
        content = body
        if content is None:
            content = "---\nname: %s\ndescription: %s\n---\n\n# Body\n" % (name, description)
        (directory / "SKILL.md").write_text(content, encoding="utf-8")
        return directory

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="prodoc-skill-")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def test_repository_skill_passes(self):
        proc = run([sys.executable, str(CHECK_SKILL), str(REPO_ROOT), "--json"])
        payload = json.loads(proc.stdout)
        self.assertEqual(proc.returncode, 0, payload)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["errors"], 0)

    def test_name_directory_mismatch_is_rejected(self):
        odd = self.make_skill(self.tmp, name="dir-name", body=(
            "---\nname: other-name\ndescription: Does a thing. Use when needed.\n---\n\nBody\n"
        ))
        proc = run([sys.executable, str(CHECK_SKILL), str(odd)])
        self.assertEqual(proc.returncode, 1)
        self.assertIn("parent directory name", proc.stdout)

    def test_uppercase_name_is_rejected(self):
        directory = Path(self.tmp) / "Upper-Case"
        directory.mkdir()
        (directory / "SKILL.md").write_text(
            "---\nname: Upper-Case\ndescription: Does a thing. Use when needed.\n---\n\nBody\n",
            encoding="utf-8",
        )
        proc = run([sys.executable, str(CHECK_SKILL), str(directory)])
        self.assertEqual(proc.returncode, 1)

    def test_missing_description_is_rejected(self):
        directory = self.make_skill(self.tmp, name="no-desc", body="---\nname: no-desc\n---\n\nBody\n")
        proc = run([sys.executable, str(CHECK_SKILL), str(directory)])
        self.assertEqual(proc.returncode, 1)
        self.assertIn("description", proc.stdout)

    def test_overlong_description_is_rejected(self):
        directory = self.make_skill(self.tmp, name="long-desc", description="x" * 1025)
        proc = run([sys.executable, str(CHECK_SKILL), str(directory)])
        self.assertEqual(proc.returncode, 1)

    def test_unfenced_frontmatter_is_rejected(self):
        directory = self.make_skill(self.tmp, name="no-fence", body="name: no-fence\n")
        proc = run([sys.executable, str(CHECK_SKILL), str(directory)])
        self.assertEqual(proc.returncode, 1)

    def test_missing_bundled_reference_is_rejected(self):
        directory = self.make_skill(self.tmp, name="dangling", body=(
            "---\nname: dangling\ndescription: Does a thing. Use when needed.\n---\n\n"
            "Run `scripts/ghost.py` to do it.\n"
        ))
        proc = run([sys.executable, str(CHECK_SKILL), str(directory)])
        self.assertEqual(proc.returncode, 1)
        self.assertIn("scripts/ghost.py", proc.stdout)

    def test_missing_skill_md_is_an_environment_error(self):
        proc = run([sys.executable, str(CHECK_SKILL), self.tmp])
        self.assertEqual(proc.returncode, 3)


class TemplateContractTests(unittest.TestCase):
    """The templates and the validator's section list must not drift apart."""

    @classmethod
    def setUpClass(cls):
        cls.prodoc = load_prodoc()

    def test_every_required_section_is_in_its_template(self):
        for doc, sections in self.prodoc.REQUIRED_SECTIONS.items():
            template = (TEMPLATES / doc).read_text(encoding="utf-8")
            present = {name.lower() for name in self.prodoc.split_sections(template)[0]}
            for section in sections:
                self.assertIn(section.lower(), present, "%s: template lacks '## %s'" % (doc, section))

    def test_templates_carry_placeholders_for_missing_information(self):
        with_placeholders = [
            doc
            for doc in ("PRODUCT_REQUIREMENTS.md", "PROJECT_STATUS.md")
            if "prodoc:todo" in (TEMPLATES / doc).read_text(encoding="utf-8")
        ]
        self.assertEqual(len(with_placeholders), 2)

    def test_templates_have_no_real_decisions(self):
        template = (TEMPLATES / "DECISION_LOG.md").read_text(encoding="utf-8")
        self.assertEqual(self.prodoc.parse_decisions(template)[0], [])

    def test_status_template_has_a_managed_block(self):
        template = (TEMPLATES / "PROJECT_STATUS.md").read_text(encoding="utf-8")
        block = self.prodoc.extract_verified_block(template)
        self.assertIsNotNone(block)
        for key in ("branch", "commit", "working tree", "verified at"):
            self.assertIn(key, block)


class RepositoryDocumentationTests(unittest.TestCase):
    """Publication-readiness checks that do not need a Git repository."""

    @classmethod
    def setUpClass(cls):
        cls.readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        cls.license_text = (REPO_ROOT / "LICENSE").read_text(encoding="utf-8")
        cls.compat = (REPO_ROOT / "docs" / "COMPATIBILITY.md").read_text(encoding="utf-8")

    def test_mit_licence_names_the_developer(self):
        self.assertIn("MIT License", self.license_text)
        self.assertIn("Evan Zellner", self.license_text)

    def test_readme_documents_open_code_and_codex_installation(self):
        lowered = self.readme.lower()
        self.assertIn("opencode", lowered)
        self.assertIn("codex", lowered)
        self.assertIn(".agents/skills", self.readme)

    def test_readme_states_chatgpt_limitations(self):
        lowered = self.readme.lower()
        self.assertIn("chatgpt", lowered)
        self.assertTrue(
            "not supported" in lowered or "does not" in lowered or "limitation" in lowered
        )

    def test_readme_disclaims_openai_endorsement(self):
        lowered = self.readme.lower()
        self.assertIn("not affiliated", lowered)
        self.assertIn("endorse", lowered)

    def test_compatibility_documents_platform_differences(self):
        self.assertIn("opencode", self.compat.lower())
        self.assertIn("codex", self.compat.lower())
        self.assertIn("chatgpt", self.compat.lower())

    def test_repository_has_release_artefacts(self):
        for relative in (
            "CHANGELOG.md",
            "SECURITY.md",
            "docs/TEST_REPORT.md",
            "docs/RELEASE_CHECKLIST.md",
            ".github/actions/prodoc-check/action.yml",
        ):
            self.assertTrue((REPO_ROOT / relative).exists(), "missing %s" % relative)


if __name__ == "__main__":
    unittest.main()
