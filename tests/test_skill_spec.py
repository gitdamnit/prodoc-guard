"""Specification and documentation tests for the ProDoc Guard skill itself.

These tests encode the Agent Skills rules from
https://agentskills.io/specification and check this repository's own artefacts:
SKILL.md frontmatter, progressive-disclosure budgets, bundled-file references,
template/section agreement, and the documentation the release depends on.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import os
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
        block, kind = self.prodoc.extract_observed_block(template)
        self.assertIsNotNone(block)
        self.assertEqual(kind, "observed")
        for key in ("observed branch", "observed commit", "observed working tree", "observed at"):
            self.assertIn(key, block)
        self.assertIn("not evidence", template)

    def test_status_template_separates_observation_from_verification(self):
        template = (TEMPLATES / "PROJECT_STATUS.md").read_text(encoding="utf-8")
        sections = {name.lower() for name in self.prodoc.split_sections(template)[0]}
        self.assertIn("repository state", sections)
        self.assertIn("verification evidence", sections)
        self.assertNotIn("verified state", sections)

    def test_required_sections_avoid_verified_wording(self):
        for doc, sections in self.prodoc.REQUIRED_SECTIONS.items():
            for section in sections:
                self.assertNotIn(
                    "verified",
                    section.lower(),
                    "%s requires a section named %r, which implies the CLI verifies the implementation"
                    % (doc, section),
                )


class VendorNeutralityTests(unittest.TestCase):
    """The core must not depend on any AI vendor, and must be auditable as such."""

    #: modules the shipped scripts are allowed to import
    STDLIB_ALLOWLIST = {
        "__future__",
        "argparse",
        "datetime",
        "hashlib",
        "importlib",
        "json",
        "os",
        "pathlib",
        "re",
        "shutil",
        "stat",
        "subprocess",
        "sys",
        "tempfile",
        "yaml",  # optional: only imported inside try/except for frontmatter parsing
    }

    REQUIRED_CLIENTS = (
        "opencode",
        "codex",
        "claude code",
        "cursor",
        "github copilot",
        "gemini cli",
        "chatgpt",
    )
    STATES = ("specification-conformant", "runtime-tested", "unverified", "unsupported", "planned")

    #: other projects this repository must stay independent from
    OTHER_PROJECTS = (
        "Bludit Wizard",
        "TRAVIS",
        "Stranger Danger",
        "Git That Shit",
        "Checkpoint Orchestrator",
    )

    def test_shipped_scripts_import_standard_library_only(self):
        import ast

        offenders = {}
        for path in (REPO_ROOT / "scripts" / "prodoc", REPO_ROOT / "scripts" / "check_skill.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            modules = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    modules.update(alias.name.split(".")[0] for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    modules.add(node.module.split(".")[0])
            extra = modules - self.STDLIB_ALLOWLIST
            if extra:
                offenders[path.name] = sorted(extra)
        self.assertEqual(offenders, {}, "non-stdlib imports in shipped scripts: %s" % offenders)

    def test_shipped_scripts_use_no_network_modules(self):
        forbidden = ("socket", "urllib", "http", "requests", "httpx", "aiohttp", "ftplib", "smtplib", "ssl")
        for path in (REPO_ROOT / "scripts" / "prodoc", REPO_ROOT / "scripts" / "check_skill.py"):
            text = path.read_text(encoding="utf-8")
            for module in forbidden:
                self.assertNotIn("import %s" % module, text, "%s imports %s" % (path.name, module))

    def test_skill_md_uses_no_vendor_namespaced_metadata(self):
        text = SKILL_MD.read_text(encoding="utf-8")
        for namespace in ("opencode/", "claude/", "cursor/", "copilot/", "gemini/", "openai/"):
            self.assertNotIn(namespace, text, "vendor-namespaced key %r in the portable SKILL.md" % namespace)

    def test_skill_md_declares_vendor_neutrality(self):
        lowered = SKILL_MD.read_text(encoding="utf-8").lower()
        self.assertIn("vendor-neutral", lowered)
        self.assertIn("no vendor sdk", lowered)

    def test_compatibility_matrix_covers_the_required_clients(self):
        text = (REPO_ROOT / "docs" / "COMPATIBILITY.md").read_text(encoding="utf-8").lower()
        for client in self.REQUIRED_CLIENTS:
            self.assertIn(client, text, "compatibility matrix does not mention %s" % client)

    def test_compatibility_matrix_uses_five_states(self):
        text = (REPO_ROOT / "docs" / "COMPATIBILITY.md").read_text(encoding="utf-8")
        lowered = text.lower()
        for state in self.STATES:
            self.assertIn("**%s**" % state.lower(), lowered, "status label %r missing" % state)

    def test_no_client_is_labelled_runtime_tested(self):
        """A client row may only claim a runtime test if one is recorded."""
        text = (REPO_ROOT / "docs" / "COMPATIBILITY.md").read_text(encoding="utf-8")
        matrix = text.split("## Compatibility matrix", 1)[1].split("\n## ", 1)[0]
        rows = [line for line in matrix.splitlines() if line.startswith("| **")]
        offenders = [
            line
            for line in rows
            if "**runtime-tested**" in line.lower() and "not by a client" not in line
        ]
        for line in offenders:
            self.assertIn(
                "docs/runtime",
                line,
                "row claims a runtime test without pointing at recorded evidence: %s" % line[:120],
            )

    def test_compatibility_matrix_separates_conformance_from_runtime(self):
        text = (REPO_ROOT / "docs" / "COMPATIBILITY.md").read_text(encoding="utf-8")
        lowered = text.lower()
        self.assertIn("specification-conformant", lowered)
        self.assertIn("runtime-tested", lowered)
        self.assertIn("no client was launched", lowered)
        self.assertNotIn("**Verified**", text)

    def test_portable_install_path_is_documented(self):
        for relative in ("README.md", "docs/COMPATIBILITY.md"):
            text = (REPO_ROOT / relative).read_text(encoding="utf-8")
            self.assertIn(".agents/skills", text, "%s does not document the portable path" % relative)

    def test_other_projects_appear_only_in_exclusion_statements(self):
        """Independence from unrelated projects, enforced by where the names may appear."""
        import re

        pattern = re.compile("|".join(re.escape(name) for name in self.OTHER_PROJECTS), re.IGNORECASE)
        negation = re.compile(r"\b(not|never|no|independent|exclud|unrelated)\b", re.IGNORECASE)

        # code must not mention them at all
        for path in sorted((REPO_ROOT / "scripts").iterdir()):
            if path.is_file():
                self.assertIsNone(
                    pattern.search(path.read_text(encoding="utf-8")),
                    "%s references another project" % path.name,
                )
        # documents may mention them only inside an exclusion statement
        # (the sentence may wrap, so inspect a window of characters around each hit)
        for name in ("SKILL.md", "README.md", "PRODUCT_REQUIREMENTS.md", "PROJECT_STATUS.md", "DECISION_LOG.md"):
            text = (REPO_ROOT / name).read_text(encoding="utf-8")
            for match in pattern.finditer(text):
                window = text[max(0, match.start() - 220) : match.end() + 220]
                self.assertIsNotNone(
                    negation.search(window),
                    "%s mentions another project without excluding it: %r"
                    % (name, window.strip()[:120]),
                )

    def test_optional_adapters_are_documented_not_vendored(self):
        text = (REPO_ROOT / "docs" / "COMPATIBILITY.md").read_text(encoding="utf-8")
        self.assertIn("Optional local adapters", text)
        self.assertIn("opencode/slash", text)
        # and the OpenCode metadata field is described as a local copy edit
        self.assertIn("your local copy", text)


class TestRunnerTests(unittest.TestCase):
    """P2: generated reports must not silently overwrite tracked evidence.

    These tests invoke `run_tests.py`, which would otherwise discover and re-run
    this class, recursing until the timeout fires. A nested run is therefore
    tagged with PRODOC_NESTED_TEST_RUN and skips these cases at depth >= 2. This
    guard also keeps the suite fast: the recursion made a full run take over
    twelve minutes instead of roughly one.
    """

    @classmethod
    def setUpClass(cls):
        loader = importlib.machinery.SourceFileLoader("prodoc_run_tests", str(REPO_ROOT / "tests" / "run_tests.py"))
        spec = importlib.util.spec_from_loader(loader.name, loader)
        cls.runner = importlib.util.module_from_spec(spec)
        loader.exec_module(cls.runner)

    def setUp(self):
        if os.environ.get("PRODOC_NESTED_TEST_RUN"):
            self.skipTest("already inside a nested test-runner invocation")
        self.tmp = tempfile.mkdtemp(prefix="prodoc-runner-")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def nested_env(self):
        env = dict(os.environ)
        env["PRODOC_NESTED_TEST_RUN"] = "1"
        return env

    def test_default_output_is_outside_the_tracked_tree(self):
        json_path, report_path, mode = self.runner.output_paths(REPO_ROOT)
        self.assertEqual(mode, "scratch")
        self.assertEqual(json_path.parent.name, self.runner.DEFAULT_OUTPUT_DIRNAME)
        self.assertNotIn("docs", json_path.parts)
        self.assertNotIn("docs", report_path.parts)

    def test_default_output_directory_is_gitignored(self):
        ignored = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")
        self.assertIn(self.runner.DEFAULT_OUTPUT_DIRNAME, ignored)

    def test_update_evidence_targets_docs(self):
        json_path, report_path, mode = self.runner.output_paths(REPO_ROOT, update_evidence=True)
        self.assertEqual(mode, "evidence")
        self.assertEqual(json_path, REPO_ROOT / "docs" / "test-results.json")
        self.assertEqual(report_path, REPO_ROOT / "docs" / "TEST_REPORT.md")

    def test_custom_output_directory_is_honoured(self):
        target = Path(self.tmp) / "somewhere"
        json_path, _report, mode = self.runner.output_paths(REPO_ROOT, output_dir=str(target))
        self.assertEqual(mode, "custom")
        self.assertEqual(json_path.parent, target)

    def test_overwrite_guard_refuses_existing_evidence(self):
        existing = Path(self.tmp) / "test-results.json"
        existing.write_text("{}", encoding="utf-8")
        message = self.runner.evidence_overwrite_guard([existing], True, False)
        self.assertIsNotNone(message)
        self.assertIn("refusing to overwrite", message)
        self.assertIn("--force", message)

    def test_overwrite_guard_allows_force(self):
        existing = Path(self.tmp) / "test-results.json"
        existing.write_text("{}", encoding="utf-8")
        self.assertIsNone(self.runner.evidence_overwrite_guard([existing], True, True))

    def test_overwrite_guard_ignores_scratch_runs(self):
        existing = Path(self.tmp) / "test-results.json"
        existing.write_text("{}", encoding="utf-8")
        self.assertIsNone(self.runner.evidence_overwrite_guard([existing], False, False))

    def test_runner_default_run_writes_scratch_and_leaves_docs_alone(self):
        """End to end: a normal run must not modify the tracked evidence."""
        evidence = REPO_ROOT / "docs" / "test-results.json"
        before = evidence.read_bytes() if evidence.exists() else None
        output = Path(self.tmp) / "out"
        proc = subprocess.run(
            [sys.executable, str(REPO_ROOT / "tests" / "run_tests.py"),
             "--quiet", "--no-gates", "--pattern", "test_skill_spec.py", "--output", str(output)],
            cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=300, env=self.nested_env(),
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertTrue((output / "test-results.json").is_file())
        self.assertTrue((output / "TEST_REPORT.md").is_file())
        after = evidence.read_bytes() if evidence.exists() else None
        self.assertEqual(before, after, "docs/test-results.json must be untouched")

    def test_update_evidence_without_force_is_refused(self):
        proc = subprocess.run(
            [sys.executable, str(REPO_ROOT / "tests" / "run_tests.py"), "--quiet", "--no-gates",
             "--pattern", "test_skill_spec.py", "--update-evidence"],
            cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=300, env=self.nested_env(),
        )
        self.assertEqual(proc.returncode, 2)
        self.assertIn("refusing to overwrite", proc.stderr)


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
