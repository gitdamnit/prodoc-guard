"""End-to-end tests for the prodoc CLI against disposable Git repositories.

Covers: initialization, missing-document recovery, preservation of existing
content, clean and dirty working trees, multiple branches and detached HEAD,
concurrent modification, read-only targets, invalid and missing remotes,
idempotency, append-only decision history, false-completion prevention,
fabricated test results, secret detection and redaction, non-mutating Git
behaviour, exit codes, and JSON output.
"""

from __future__ import annotations

import os
import stat
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from support import (  # noqa: E402
    CLI,
    CANONICAL_DOCS,
    RepoCase,
    load_prodoc,
    valid_decision_log,
    valid_docs,
    valid_product_requirements,
    valid_project_status,
)

VERIFIED_BLOCK = r"<!-- prodoc:verified:start -->.*?<!-- prodoc:verified:end -->"


def fake_aws_key():
    """Assembled at runtime so no scanner has to tolerate a literal in this file."""
    return "AKIA" + "QQ7XZ5RT81N4M6L2"


class InitTests(RepoCase):
    def test_init_creates_three_documents(self):
        proc, payload = self.cli_json("init")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        for doc in CANONICAL_DOCS:
            self.assertTrue((self.repo / doc).is_file(), doc)
        actions = {a["file"]: a["action"] for a in payload["info"]["actions"]}
        self.assertEqual(actions, {doc: "created" for doc in CANONICAL_DOCS})

    def test_init_is_idempotent(self):
        self.assertEqual(self.cli("init").returncode, 0)
        first = {doc: self.read(doc) for doc in CANONICAL_DOCS}
        proc, payload = self.cli_json("init")
        self.assertEqual(proc.returncode, 0)
        second = {doc: self.read(doc) for doc in CANONICAL_DOCS}
        self.assertEqual(first, second)
        self.assertEqual({a["action"] for a in payload["info"]["actions"]}, {"kept"})
        self.assertIn("init.noop", self.codes(payload, "info"))

    def test_init_never_overwrites_existing_content(self):
        custom = "# Project Status\n\nhand-written, do not clobber\n"
        (self.repo / "PROJECT_STATUS.md").write_text(custom, encoding="utf-8")
        proc, payload = self.cli_json("init")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(self.read("PROJECT_STATUS.md"), custom)
        actions = {a["file"]: a["action"] for a in payload["info"]["actions"]}
        self.assertEqual(actions["PROJECT_STATUS.md"], "kept")
        self.assertEqual(actions["PRODUCT_REQUIREMENTS.md"], "created")

    def test_init_dry_run_writes_nothing(self):
        proc, payload = self.cli_json("init", "--dry-run")
        self.assertEqual(proc.returncode, 0)
        for doc in CANONICAL_DOCS:
            self.assertFalse((self.repo / doc).exists(), doc)
        self.assertEqual(
            {a["action"] for a in payload["info"]["actions"]}, {"would-create"}
        )

    def test_init_missing_templates_is_environment_error(self):
        proc = self.cli("init", "--templates", str(self.repo / "nope"))
        self.assertEqual(proc.returncode, 3)

    def test_templates_dir_resolves_from_script_location(self):
        """init must work from an unrelated cwd without PRODOC_TEMPLATES."""
        outside = Path(self._tmp) / "elsewhere"
        outside.mkdir()
        proc = self.cli("init", "--repo", str(self.repo), cwd=outside)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertTrue((self.repo / "PRODUCT_REQUIREMENTS.md").is_file())


class ValidateTests(RepoCase):
    def test_fresh_init_fails_validation_until_filled(self):
        self.cli("init")
        proc, payload = self.cli_json("validate")
        self.assertEqual(proc.returncode, 1)
        self.assertIn("doc.placeholder", self.codes(payload, "error"))
        # fenced examples in the templates must not be mistaken for real records
        self.assertNotIn("log.field", self.codes(payload, "error"))

    def test_valid_documents_pass(self):
        self.write_docs()
        proc, payload = self.cli_json("validate")
        self.assertEqual(proc.returncode, 0, payload)
        self.assertEqual(self.errors(payload), [])

    def test_missing_document_is_an_error(self):
        docs = valid_docs()
        del docs["DECISION_LOG.md"]
        self.write_docs(docs)
        proc, payload = self.cli_json("validate")
        self.assertEqual(proc.returncode, 1)
        self.assertIn("doc.missing", self.codes(payload, "error"))

    def test_missing_section_is_named(self):
        text = valid_product_requirements().replace("## Purpose\n", "")
        docs = valid_docs()
        docs["PRODUCT_REQUIREMENTS.md"] = text
        self.write_docs(docs)
        proc, payload = self.cli_json("validate")
        self.assertEqual(proc.returncode, 1)
        messages = " ".join(f["message"] for f in self.errors(payload))
        self.assertIn("Purpose", messages)

    def test_decision_missing_field_is_named(self):
        text = valid_decision_log().replace("- **Rationale:** because\n", "")
        docs = valid_docs()
        docs["DECISION_LOG.md"] = text
        self.write_docs(docs)
        proc, payload = self.cli_json("validate")
        self.assertEqual(proc.returncode, 1)
        self.assertIn("log.field", self.codes(payload, "error"))
        self.assertIn("Rationale", " ".join(f["message"] for f in self.errors(payload)))

    def test_duplicate_decision_id_is_rejected(self):
        text = valid_decision_log() + valid_decision_log(decision_id="D-0001").split("## Decisions", 1)[1]
        docs = valid_docs()
        docs["DECISION_LOG.md"] = text
        self.write_docs(docs)
        proc, payload = self.cli_json("validate")
        self.assertEqual(proc.returncode, 1)
        self.assertIn("log.duplicate", self.codes(payload, "error"))

    def test_out_of_order_decision_ids_are_rejected(self):
        first = valid_decision_log(decision_id="D-0002")
        second_block = valid_decision_log(decision_id="D-0001").split("### D-0001")[1]
        docs = valid_docs()
        docs["DECISION_LOG.md"] = first + "\n### D-0001" + second_block
        self.write_docs(docs)
        proc, payload = self.cli_json("validate")
        self.assertEqual(proc.returncode, 1)
        self.assertIn("log.order", self.codes(payload, "error"))

    def test_fenced_decision_example_is_not_a_record(self):
        docs = valid_docs()
        docs["DECISION_LOG.md"] = valid_decision_log(with_decision=False)
        self.write_docs(docs)
        proc, payload = self.cli_json("validate")
        self.assertEqual(proc.returncode, 0, payload)
        self.assertIn("log.empty", self.codes(payload, "warning"))

    def test_unknown_phase_is_a_warning(self):
        docs = valid_docs()
        docs["PROJECT_STATUS.md"] = valid_project_status(phase="Faffing About")
        self.write_docs(docs)
        proc, payload = self.cli_json("validate")
        self.assertEqual(proc.returncode, 0)
        self.assertIn("status.phase", self.codes(payload, "warning"))

    def test_completed_work_state_outside_vocabulary_is_rejected(self):
        docs = valid_docs()
        docs["PROJECT_STATUS.md"] = valid_project_status(work=["- [Mostly Done] Something"])
        self.write_docs(docs)
        proc, payload = self.cli_json("validate")
        self.assertEqual(proc.returncode, 1)
        self.assertIn("status.work.state", self.codes(payload, "error"))

    def test_claim_without_evidence_is_rejected(self):
        docs = valid_docs()
        docs["PROJECT_STATUS.md"] = valid_project_status(
            work=["- [Tested] The parser handles every edge case"]
        )
        self.write_docs(docs)
        proc, payload = self.cli_json("validate")
        self.assertEqual(proc.returncode, 1)
        self.assertIn("status.work.evidence", self.codes(payload, "error"))

    def test_claim_with_evidence_is_accepted(self):
        docs = valid_docs()
        (self.repo / "src").mkdir(exist_ok=True)
        (self.repo / "src" / "parser.py").write_text("# fixture\n", encoding="utf-8")
        docs["PROJECT_STATUS.md"] = valid_project_status(
            work=["- [Implemented] Added the parser — `src/parser.py`"]
        )
        self.write_docs(docs)
        proc, payload = self.cli_json("validate")
        self.assertEqual(proc.returncode, 0, payload)

    def test_fabricated_test_result_is_rejected(self):
        docs = valid_docs()
        docs["PROJECT_STATUS.md"] = valid_project_status(
            tests_rows=["| unit | `python3 -m unittest` | Pass (31) | - |"]
        )
        self.write_docs(docs)
        proc, payload = self.cli_json("validate")
        self.assertEqual(proc.returncode, 1)
        self.assertIn("status.tests.evidence", self.codes(payload, "error"))

    def test_honest_not_run_result_is_accepted(self):
        docs = valid_docs()
        docs["PROJECT_STATUS.md"] = valid_project_status(
            tests_rows=["| manual | eyeballed it | Not run | - |"]
        )
        self.write_docs(docs)
        proc, payload = self.cli_json("validate")
        self.assertEqual(proc.returncode, 0, payload)

    def test_test_result_evidence_must_exist(self):
        docs = valid_docs()
        docs["PROJECT_STATUS.md"] = valid_project_status(
            tests_rows=["| unit | `python3 -m unittest` | Pass (1) | `docs/absent.json` |"]
        )
        self.write_docs(docs)
        proc, payload = self.cli_json("validate")
        self.assertEqual(proc.returncode, 1)
        self.assertIn("status.tests.evidence_missing", self.codes(payload, "error"))

    def test_test_result_evidence_that_exists_is_accepted(self):
        docs = valid_docs()
        (self.repo / "docs").mkdir(exist_ok=True)
        (self.repo / "docs" / "test-results.json").write_text("{}\n", encoding="utf-8")
        docs["PROJECT_STATUS.md"] = valid_project_status(
            tests_rows=["| unit | `python3 -m unittest` | Pass (1) | `docs/test-results.json` |"]
        )
        self.write_docs(docs)
        proc, payload = self.cli_json("validate")
        self.assertEqual(proc.returncode, 0, payload)


class StatusTests(RepoCase):
    def test_reports_branch_commit_and_tree(self):
        self.write_docs()
        sha = self.commit_all("docs: fixture")
        proc, payload = self.cli_json("status")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(payload["info"]["git"]["commit"], sha)
        self.assertEqual(payload["info"]["git"]["working_tree"], "clean")
        self.assertFalse(payload["info"]["git"]["detached"])
        for doc in CANONICAL_DOCS:
            self.assertTrue(payload["info"]["documents"][doc]["present"])

    def test_dirty_tree_is_reported(self):
        self.write_docs()
        self.commit_all("docs: fixture")
        (self.repo / "PRODUCT_REQUIREMENTS.md").write_text("changed\n", encoding="utf-8")
        _proc, payload = self.cli_json("status")
        self.assertEqual(payload["info"]["git"]["working_tree"], "dirty")
        self.assertIn("git.dirty", self.codes(payload, "warning"))

    def test_detached_head_is_handled(self):
        self.write_docs()
        self.commit_all("docs: fixture")
        self.git("checkout", "-q", "--detach", "HEAD")
        proc, payload = self.cli_json("status")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertTrue(payload["info"]["git"]["detached"])
        self.assertIsNone(payload["info"]["git"]["branch"])
        self.assertIn("git.detached", self.codes(payload, "warning"))
        self.assertEqual(self.branch(), "HEAD")

    def test_multiple_branches_and_cli_does_not_switch(self):
        self.write_docs()
        self.commit_all("docs: fixture")
        self.git("checkout", "-q", "-b", "feature")
        _proc, payload = self.cli_json("status")
        self.assertEqual(payload["info"]["git"]["branch"], "feature")
        self.cli("check")
        self.cli("update")
        self.assertEqual(self.branch(), "feature")

    def test_missing_remote_is_reported(self):
        _proc, payload = self.cli_json("status")
        self.assertEqual(payload["info"]["git"]["remotes"], {})
        self.assertIn("git.no_remote", self.codes(payload, "warning"))

    def test_invalid_remote_is_reported_and_credentials_redacted(self):
        secret = "s3cr3t-token-value"
        self.git("remote", "add", "origin", "https://user:%s@invalid.invalid/nope.git" % secret)
        proc, payload = self.cli_json("status")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("<redacted>", payload["info"]["git"]["remotes"]["origin"])
        self.assertNotIn(secret, proc.stdout)

    def test_status_works_without_git_binary(self):
        empty_path = Path(self._tmp) / "empty-path"
        empty_path.mkdir()
        env = dict(self.env)
        env["PATH"] = str(empty_path)
        import support

        proc = support.run_cli(["status", "--json"], self.repo, env)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = __import__("json").loads(proc.stdout)
        self.assertIn("git.missing", [f["code"] for f in payload["findings"]])


class CheckTests(RepoCase):
    def test_secret_is_detected_and_redacted(self):
        key = fake_aws_key()
        docs = valid_docs()
        docs["PRODUCT_REQUIREMENTS.md"] = valid_product_requirements() + (
            "\nPaste this key into the deploy config when needed.\n\n    key = %s\n" % key
        )
        self.write_docs(docs)
        proc, payload = self.cli_json("check")
        self.assertEqual(proc.returncode, 1)
        self.assertIn("security.secret", self.codes(payload, "error"))
        self.assertNotIn(key, proc.stdout)
        self.assertIn(key[:4] + "*" * (len(key) - 4), proc.stdout)

    def test_clean_documents_pass_the_secret_scan(self):
        self.write_docs()
        proc, payload = self.cli_json("check")
        self.assertEqual(proc.returncode, 0, payload)
        self.assertNotIn("security.secret", self.codes(payload))

    def test_append_only_violation_is_detected(self):
        two = valid_decision_log() + (
            "\n### D-0002 — Second fixture decision\n\n"
            "- **Date:** 2026-01-02\n"
            "- **Status:** Accepted\n"
            "- **Context:** second\n"
            "- **Alternatives Considered:** none\n"
            "- **Decision:** also do\n"
            "- **Rationale:** reasons\n"
            "- **Consequences:** more\n"
            "- **Supersedes:** None\n"
        )
        docs = valid_docs()
        docs["DECISION_LOG.md"] = two
        self.write_docs(docs)
        self.commit_all("docs: two decisions")

        # silently delete a committed decision
        rewritten = docs["DECISION_LOG.md"].replace("### D-0002 — Second fixture decision", "### D-0002 — was here")
        (self.repo / "DECISION_LOG.md").write_text(rewritten, encoding="utf-8")
        proc, payload = self.cli_json("check")
        self.assertEqual(proc.returncode, 0, "a rewrite keeps the id; not a violation yet")

        deleted = two.split("### D-0002")[0]
        (self.repo / "DECISION_LOG.md").write_text(deleted, encoding="utf-8")
        proc, payload = self.cli_json("check")
        self.assertEqual(proc.returncode, 1)
        self.assertIn("log.append_only", self.codes(payload, "error"))

    def test_unknown_recorded_commit_is_an_error(self):
        docs = valid_docs()
        docs["PROJECT_STATUS.md"] = valid_project_status(commit="d" * 40, tree="clean")
        self.write_docs(docs)
        proc, payload = self.cli_json("check")
        self.assertEqual(proc.returncode, 1)
        self.assertIn("status.commit_unknown", self.codes(payload, "error"))

    def test_stale_recorded_commit_is_a_warning_not_an_error(self):
        docs = valid_docs()
        self.write_docs(docs)
        first = self.commit_all("docs: fixture")
        status = valid_project_status(commit=first, tree="clean")
        (self.repo / "PROJECT_STATUS.md").write_text(status, encoding="utf-8")
        self.commit_all("docs: verified state")
        (self.repo / "README.md").write_text("unrelated\n", encoding="utf-8")
        self.commit_all("chore: unrelated")

        proc, payload = self.cli_json("check")
        self.assertEqual(proc.returncode, 0, payload)
        self.assertIn("status.stale", self.codes(payload, "warning"))

    def test_missing_referenced_path_is_a_warning(self):
        docs = valid_docs()
        docs["PROJECT_STATUS.md"] = valid_project_status(
            work=["- [Implemented] Added the widget — `src/widget.py`"]
        )
        self.write_docs(docs)
        proc, payload = self.cli_json("check")
        self.assertIn("status.path_missing", self.codes(payload, "warning"))

    def test_missing_documents_are_errors(self):
        proc, payload = self.cli_json("check")
        self.assertEqual(proc.returncode, 1)
        self.assertEqual(self.codes(payload, "error").count("doc.missing"), 3)


class UpdateTests(RepoCase):
    def test_update_refreshes_only_the_verified_block(self):
        self.write_docs()
        sha = self.commit_all("docs: fixture")
        before = self.read("PROJECT_STATUS.md")
        proc, payload = self.cli_json("update")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        after = self.read("PROJECT_STATUS.md")

        import re

        strip = lambda t: re.sub(VERIFIED_BLOCK, "", t, flags=re.DOTALL)
        self.assertEqual(strip(before), strip(after))
        self.assertEqual(payload["info"]["facts"]["commit"], sha)
        self.assertEqual(payload["info"]["facts"]["working tree"], "clean")
        self.assertIn(sha, after)

    def test_update_dry_run_writes_nothing(self):
        self.write_docs()
        self.commit_all("docs: fixture")
        before = self.read("PROJECT_STATUS.md")
        _proc, payload = self.cli_json("update", "--dry-run")
        self.assertTrue(payload["info"]["dry_run"])
        self.assertTrue(payload["info"]["changed"])
        self.assertEqual(self.read("PROJECT_STATUS.md"), before)

    def test_update_without_markers_fails(self):
        (self.repo / "PROJECT_STATUS.md").write_text("# Project Status\n", encoding="utf-8")
        proc = self.cli("update")
        self.assertEqual(proc.returncode, 1)

    def test_update_records_dirty_tree_honestly(self):
        self.write_docs()  # uncommitted: the tree is dirty
        _proc, payload = self.cli_json("update")
        self.assertEqual(payload["info"]["facts"]["working tree"], "dirty")

    def test_update_rejects_unknown_phase(self):
        self.write_docs()
        proc = self.cli("update", "--phase", "Vibing")
        self.assertEqual(proc.returncode, 2)

    def test_update_sets_explicit_phase(self):
        self.write_docs()
        self.commit_all("docs: fixture")
        proc, payload = self.cli_json("update", "--phase", "In Progress")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(payload["info"]["facts"]["working tree"], "clean")
        self.assertIn("In Progress", self.read("PROJECT_STATUS.md"))

    def test_update_without_commits_warns_not_fails(self):
        self.write_docs()
        proc, payload = self.cli_json("update")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(payload["info"]["facts"]["commit"], "-")
        self.assertIn("update.no_commits", self.codes(payload, "warning"))


class SafetyTests(RepoCase):
    def test_concurrent_modification_is_refused(self):
        prodoc = load_prodoc()
        target = self.repo / "PROJECT_STATUS.md"
        target.write_text("original\n", encoding="utf-8")
        expected = prodoc.sha256_text("original\n")
        # somebody else writes between our read and our write
        target.write_text("changed underneath\n", encoding="utf-8")
        with self.assertRaises(prodoc.ProdocError) as caught:
            prodoc.write_atomic(target, "ours\n", expected_sha=expected)
        self.assertEqual(caught.exception.exit_code, 4)
        self.assertEqual(target.read_text(encoding="utf-8"), "changed underneath\n")

    def test_read_only_file_is_refused(self):
        if hasattr(os, "geteuid") and os.geteuid() == 0:
            self.skipTest("permission checks are bypassed when running as root")
        self.write_docs()
        self.commit_all("docs: fixture")
        target = self.repo / "PROJECT_STATUS.md"
        os.chmod(target, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
        self.addCleanup(os.chmod, target, 0o644)
        proc = self.cli("update")
        self.assertEqual(proc.returncode, 4)
        self.assertIn("read-only", proc.stderr.lower())

    def test_read_only_directory_init_is_refused(self):
        if hasattr(os, "geteuid") and os.geteuid() == 0:
            self.skipTest("permission checks are bypassed when running as root")
        os.chmod(self.repo, 0o555)
        self.addCleanup(os.chmod, self.repo, 0o755)
        proc = self.cli("init")
        self.assertEqual(proc.returncode, 4)
        self.assertIn("read-only", proc.stderr.lower())

    def test_cli_never_mutates_git_state(self):
        self.write_docs()
        self.commit_all("docs: fixture")
        before = {
            "head": self.head(),
            "count": self.git("rev-list", "--count", "HEAD").stdout.strip(),
            "branch": self.branch(),
            "reflog": len(self.git("reflog").stdout.splitlines()),
        }
        for args in (("init",), ("validate",), ("status",), ("check",), ("update",), ("update", "--dry-run")):
            self.cli(*args)
        after = {
            "head": self.head(),
            "count": self.git("rev-list", "--count", "HEAD").stdout.strip(),
            "branch": self.branch(),
            "reflog": len(self.git("reflog").stdout.splitlines()),
        }
        self.assertEqual(before, after)
        self.assertEqual(self.git("diff", "--cached", "--name-only").stdout.strip(), "")
        self.assertEqual(self.git("stash", "list").stdout.strip(), "")


class InterfaceTests(RepoCase):
    def test_json_schema_is_stable(self):
        self.write_docs()
        for command in ("init", "validate", "status", "check", "update"):
            proc, payload = self.cli_json(command)
            self.assertIsNotNone(payload, "%s produced no JSON" % command)
            for key in ("command", "ok", "exit_code", "findings", "info", "version"):
                self.assertIn(key, payload, command)
            self.assertEqual(payload["command"], command)
            self.assertEqual(proc.returncode, payload["exit_code"])

    def test_unknown_command_is_a_usage_error(self):
        proc = self.cli("frobnicate")
        self.assertEqual(proc.returncode, 2)

    def test_bad_flag_is_a_usage_error(self):
        proc = self.cli("status", "--nonsense")
        self.assertEqual(proc.returncode, 2)

    def test_missing_repo_path_is_an_environment_error(self):
        proc = self.cli("status", "--repo", str(Path(self._tmp) / "absent"))
        self.assertEqual(proc.returncode, 3)

    def test_repo_flag_targets_another_directory(self):
        self.write_docs()
        outside = Path(self._tmp) / "elsewhere"
        outside.mkdir()
        proc = self.cli("validate", "--repo", str(self.repo), cwd=outside)
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_quiet_suppresses_success_output(self):
        self.write_docs()
        proc = self.cli("validate", "--quiet")
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(proc.stdout.strip(), "")

    def test_no_command_prints_help_and_exits_two(self):
        proc = self.cli()
        self.assertEqual(proc.returncode, 2)
        self.assertIn("usage", proc.stdout.lower() + proc.stderr.lower())


class EmptyRepositoryTests(RepoCase):
    """A Git repository with no commits yet (unborn HEAD)."""

    def test_status_reports_unborn_branch_without_crashing(self):
        self.write_docs()
        proc, payload = self.cli_json("status")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("root", payload["info"]["git"])
        self.assertNotIn("commit", payload["info"]["git"])
        self.assertFalse(payload["info"]["git"]["detached"])
        self.assertIsNotNone(payload["info"]["git"]["branch"])

    def test_validate_and_update_work_before_the_first_commit(self):
        self.write_docs()
        self.assertEqual(self.cli("validate").returncode, 0)
        self.assertEqual(self.cli("update").returncode, 0)


class NonGitDirectoryTests(RepoCase):
    init_git = False

    def test_documents_work_without_git(self):
        proc = self.cli("init")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.write_docs()
        proc, payload = self.cli_json("validate")
        self.assertEqual(proc.returncode, 0, payload)
        proc, payload = self.cli_json("status")
        self.assertEqual(proc.returncode, 0)
        self.assertIn("git.none", self.codes(payload, "warning"))
        proc, payload = self.cli_json("check")
        self.assertEqual(proc.returncode, 0, payload)
        self.assertIn("log.no_git", self.codes(payload, "info"))
        _proc, payload = self.cli_json("update")
        self.assertEqual(payload["info"]["facts"]["branch"], "-")


if __name__ == "__main__":
    unittest.main()
