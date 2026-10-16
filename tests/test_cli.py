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
    CANONICAL_DOCS,
    REPO_ROOT as ROOT,
    RepoCase,
    load_prodoc,
    run_git,
    valid_decision_log,
    valid_docs,
    valid_product_requirements,
    valid_project_status,
)

STATE_BLOCK = r"<!-- prodoc:(?:observed|verified):start -->.*?<!-- prodoc:(?:observed|verified):end -->"


def fake_aws_key():
    """Assembled at runtime so no scanner has to tolerate a literal in this file."""
    return "AKIA" + "QQ7XZ5RT81N4M6L2"


def two_decision_log():
    """The base fixture plus D-0002, for append-only and mutation tests."""
    return valid_decision_log() + (
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
        two = two_decision_log()
        docs = valid_docs()
        docs["DECISION_LOG.md"] = two
        self.write_docs(docs)
        self.commit_all("docs: two decisions")

        # renaming a record keeps the id: that is a modification, not a deletion
        rewritten = two.replace("### D-0002 — Second fixture decision", "### D-0002 — was here")
        (self.repo / "DECISION_LOG.md").write_text(rewritten, encoding="utf-8")
        proc, payload = self.cli_json("check")
        self.assertEqual(proc.returncode, 1, "a retitle is an edit to history")
        self.assertIn("log.modified", self.codes(payload, "error"))
        self.assertNotIn("log.append_only", self.codes(payload, "error"))

        deleted = two.split("### D-0002")[0]
        (self.repo / "DECISION_LOG.md").write_text(deleted, encoding="utf-8")
        proc, payload = self.cli_json("check")
        self.assertEqual(proc.returncode, 1)
        self.assertIn("log.append_only", self.codes(payload, "error"))

    def test_altered_decision_with_the_same_id_is_detected(self):
        """The audit's case: an edit keeps the ID, so a set comparison misses it."""
        two = two_decision_log()
        docs = valid_docs()
        docs["DECISION_LOG.md"] = two
        self.write_docs(docs)
        self.commit_all("docs: two decisions")

        tampered = two.replace(
            "- **Decision:** also do", "- **Decision:** do something else entirely"
        )
        self.assertNotEqual(tampered, two)
        (self.repo / "DECISION_LOG.md").write_text(tampered, encoding="utf-8")

        proc, payload = self.cli_json("check")
        self.assertEqual(proc.returncode, 1)
        self.assertIn("log.modified", self.codes(payload, "error"))
        messages = " ".join(f["message"] for f in self.errors(payload))
        self.assertIn("D-0002", messages)
        self.assertIn("decision", messages)

    def test_altered_decision_field_is_named(self):
        two = two_decision_log()
        docs = valid_docs()
        docs["DECISION_LOG.md"] = two
        self.write_docs(docs)
        self.commit_all("docs: two decisions")

        tampered = two.replace("- **Rationale:** reasons", "- **Rationale:** because I said so")
        (self.repo / "DECISION_LOG.md").write_text(tampered, encoding="utf-8")
        _proc, payload = self.cli_json("check")
        self.assertIn("log.modified", self.codes(payload, "error"))
        self.assertIn("rationale", " ".join(f["message"] for f in self.errors(payload)))

    def test_altered_decision_date_is_detected(self):
        two = two_decision_log()
        docs = valid_docs()
        docs["DECISION_LOG.md"] = two
        self.write_docs(docs)
        self.commit_all("docs: two decisions")

        tampered = two.replace("- **Date:** 2026-01-02", "- **Date:** 2025-12-01")
        (self.repo / "DECISION_LOG.md").write_text(tampered, encoding="utf-8")
        _proc, payload = self.cli_json("check")
        self.assertIn("log.modified", self.codes(payload, "error"))
        self.assertIn("date", " ".join(f["message"] for f in self.errors(payload)))

    def test_reordered_decisions_are_detected(self):
        two = two_decision_log()
        docs = valid_docs()
        docs["DECISION_LOG.md"] = two
        self.write_docs(docs)
        self.commit_all("docs: two decisions")

        prefix, rest = two.split("### D-0001", 1)
        d1_block = "### D-0001" + rest.split("### D-0002")[0]
        d2_block = "### D-0002" + rest.split("### D-0002")[1]
        reordered = prefix + d2_block + d1_block
        (self.repo / "DECISION_LOG.md").write_text(reordered, encoding="utf-8")
        _proc, payload = self.cli_json("check")
        self.assertIn("log.reordered", self.codes(payload, "error"))

    def test_reflowing_a_decision_is_not_an_edit(self):
        """Whitespace normalization keeps harmless rewrapping from failing the check."""
        two = two_decision_log()
        docs = valid_docs()
        docs["DECISION_LOG.md"] = two
        self.write_docs(docs)
        self.commit_all("docs: two decisions")

        reflowed = two.replace(
            "- **Decision:** also do", "- **Decision:**   also    do  "
        )
        (self.repo / "DECISION_LOG.md").write_text(reflowed, encoding="utf-8")
        proc, payload = self.cli_json("check")
        self.assertEqual(proc.returncode, 0, payload)
        self.assertNotIn("log.modified", self.codes(payload, "error"))

    def test_status_change_on_an_old_decision_is_allowed_and_reported(self):
        """Superseding a record is an intended mutation of its Status line."""
        two = two_decision_log()
        docs = valid_docs()
        docs["DECISION_LOG.md"] = two
        self.write_docs(docs)
        self.commit_all("docs: two decisions")

        superseded = two.replace(
            "- **Status:** Accepted\n- **Context:** second",
            "- **Status:** Superseded by D-0003\n- **Context:** second",
        )
        (self.repo / "DECISION_LOG.md").write_text(superseded, encoding="utf-8")
        proc, payload = self.cli_json("check")
        self.assertEqual(proc.returncode, 0, payload)
        self.assertNotIn("log.modified", self.codes(payload, "error"))
        self.assertIn("log.status_changed", self.codes(payload, "warning"))

    def test_appending_a_decision_after_others_is_accepted(self):
        two = two_decision_log()
        docs = valid_docs()
        docs["DECISION_LOG.md"] = two
        self.write_docs(docs)
        self.commit_all("docs: two decisions")

        three = two + (
            "\n### D-0003 — Third fixture decision\n\n"
            "- **Date:** 2026-01-03\n"
            "- **Status:** Accepted\n"
            "- **Context:** third\n"
            "- **Alternatives Considered:** none\n"
            "- **Decision:** append is fine\n"
            "- **Rationale:** it is the sanctioned path\n"
            "- **Consequences:** growth\n"
            "- **Supersedes:** None\n"
        )
        (self.repo / "DECISION_LOG.md").write_text(three, encoding="utf-8")
        proc, payload = self.cli_json("check")
        self.assertEqual(proc.returncode, 0, payload)
        self.assertIn("decision-history", payload["info"]["checks"])

    def test_history_check_is_reported_as_an_integrity_check_only(self):
        """The guarantee is not tamper-proofing, and the docs must say so."""
        text = (ROOT / "references" / "security.md").read_text(encoding="utf-8")
        lowered = text.lower()
        self.assertIn("tamper", lowered)
        self.assertIn("rewrite", lowered)

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

        strip = lambda t: re.sub(STATE_BLOCK, "", t, flags=re.DOTALL)
        self.assertEqual(strip(before), strip(after))
        self.assertEqual(payload["info"]["observed"]["observed commit"], sha)
        self.assertEqual(payload["info"]["observed"]["observed working tree"], "clean")
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
        self.assertEqual(payload["info"]["observed"]["observed working tree"], "dirty")

    def test_update_rejects_unknown_phase(self):
        self.write_docs()
        proc = self.cli("update", "--phase", "Vibing")
        self.assertEqual(proc.returncode, 2)

    def test_update_sets_explicit_phase(self):
        self.write_docs()
        self.commit_all("docs: fixture")
        proc, payload = self.cli_json("update", "--phase", "In Progress")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(payload["info"]["observed"]["observed working tree"], "clean")
        self.assertIn("In Progress", self.read("PROJECT_STATUS.md"))

    def test_update_without_commits_warns_not_fails(self):
        self.write_docs()
        proc, payload = self.cli_json("update")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(payload["info"]["observed"]["observed commit"], "-")
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


class VerifiedStateSemanticsTests(RepoCase):
    """P1: observed Git metadata must not be presented as verification."""

    def test_observed_block_is_labelled_as_observation(self):
        self.write_docs()
        _proc, payload = self.cli_json("update")
        observed = payload["info"]["observed"]
        for key in ("observed branch", "observed commit", "observed working tree", "observed at"):
            self.assertIn(key, observed)
        self.assertNotIn("facts", payload["info"])
        self.assertNotIn("verified at", observed)

    def test_written_block_uses_observed_markers_and_a_caveat(self):
        self.write_docs()
        self.cli("update")
        text = self.read("PROJECT_STATUS.md")
        self.assertIn("<!-- prodoc:observed:start -->", text)
        self.assertIn("<!-- prodoc:observed:end -->", text)
        self.assertIn("not evidence that the implementation or its tests are correct", text)
        self.assertNotIn("prodoc:verified:start", text)

    def test_update_output_says_it_is_not_verification(self):
        self.write_docs()
        proc = self.cli("update")
        lowered = proc.stdout.lower()
        self.assertIn("observed", lowered)
        self.assertIn("not verification", lowered)

    def test_update_does_not_write_verification_evidence(self):
        """The command observes Git; it must never invent evidence."""
        docs = valid_docs()
        docs["PROJECT_STATUS.md"] = valid_project_status(
            verification=["- **Verification:** commit `" + "a" * 40 + "` — hand checked — evidence `README.md`"]
        )
        self.write_docs(docs)
        before = self.read("PROJECT_STATUS.md")
        self.cli("update")
        after = self.read("PROJECT_STATUS.md")
        import re as _re

        strip = lambda t: _re.sub(STATE_BLOCK, "", t, flags=_re.DOTALL)
        self.assertEqual(strip(before), strip(after))
        self.assertIn("hand checked", after)

    def test_legacy_markers_still_validate_but_are_reported(self):
        docs = valid_docs()
        docs["PROJECT_STATUS.md"] = valid_project_status(legacy=True)
        self.write_docs(docs)
        proc, payload = self.cli_json("validate")
        self.assertEqual(proc.returncode, 0, payload)
        self.assertIn("doc.legacy_heading", self.codes(payload, "warning"))
        self.assertIn("status.legacy_block", self.codes(payload, "warning"))

    def test_update_migrates_the_legacy_block(self):
        docs = valid_docs()
        docs["PROJECT_STATUS.md"] = valid_project_status(legacy=True)
        self.write_docs(docs)
        proc, payload = self.cli_json("update")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("update.migrated", self.codes(payload, "info"))
        text = self.read("PROJECT_STATUS.md")
        self.assertIn("prodoc:observed:start", text)
        self.assertNotIn("prodoc:verified:start", text)
        proc, payload = self.cli_json("validate")
        self.assertEqual(proc.returncode, 0, payload)
        self.assertNotIn("status.legacy_block", self.codes(payload))

    def test_missing_observed_block_is_an_error(self):
        docs = valid_docs()
        docs["PROJECT_STATUS.md"] = valid_project_status().replace(
            "<!-- prodoc:observed:start -->", ""
        ).replace("<!-- prodoc:observed:end -->", "")
        self.write_docs(docs)
        proc, payload = self.cli_json("validate")
        self.assertEqual(proc.returncode, 1)
        self.assertIn("status.observed_block", self.codes(payload, "error"))

    def test_verification_evidence_section_is_required(self):
        docs = valid_docs()
        docs["PROJECT_STATUS.md"] = valid_project_status().replace(
            "## Verification Evidence", "## Something Else"
        )
        self.write_docs(docs)
        proc, payload = self.cli_json("validate")
        self.assertEqual(proc.returncode, 1)
        messages = " ".join(f["message"] for f in self.errors(payload))
        self.assertIn("Verification Evidence", messages)

    def test_release_phase_requires_verification_evidence(self):
        docs = valid_docs()
        docs["PROJECT_STATUS.md"] = valid_project_status(phase="Released")
        self.write_docs(docs)
        proc, payload = self.cli_json("validate")
        self.assertEqual(proc.returncode, 1)
        self.assertIn("status.release_evidence", self.codes(payload, "error"))

    def test_release_phase_accepts_recorded_evidence(self):
        (self.repo / "README.md").write_text("fixture\n", encoding="utf-8")
        sha = self.commit_all("chore: fixture")
        docs = valid_docs()
        docs["PROJECT_STATUS.md"] = valid_project_status(
            phase="Released",
            commit="-",
            verification=[
                "- **Verification:** commit `%s` — full suite green — evidence `README.md`" % sha
            ],
        )
        self.write_docs(docs)
        proc, payload = self.cli_json("validate")
        self.assertEqual(proc.returncode, 0, payload)

    def test_published_work_item_requires_verification_evidence(self):
        docs = valid_docs()
        docs["PROJECT_STATUS.md"] = valid_project_status(
            work=["- [Published] v0.1.0 released — `CHANGELOG.md`"]
        )
        self.write_docs(docs)
        proc, payload = self.cli_json("validate")
        self.assertEqual(proc.returncode, 1)
        self.assertIn("status.release_evidence", self.codes(payload, "error"))

    def test_update_refuses_a_release_phase_without_evidence(self):
        self.write_docs()
        self.commit_all("docs: fixture")
        proc = self.cli("update", "--phase", "Released")
        self.assertEqual(proc.returncode, 1)
        self.assertIn("verification evidence", proc.stderr.lower())
        self.assertNotIn("Released", self.read("PROJECT_STATUS.md"))

    def test_update_allows_a_release_phase_with_evidence(self):
        (self.repo / "README.md").write_text("fixture\n", encoding="utf-8")
        sha = self.commit_all("chore: fixture")
        docs = valid_docs()
        docs["PROJECT_STATUS.md"] = valid_project_status(
            verification=[
                "- **Verification:** commit `%s` — suite green — evidence `README.md`" % sha
            ]
        )
        self.write_docs(docs)
        proc = self.cli("update", "--phase", "Released")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("Released", self.read("PROJECT_STATUS.md"))

    def test_verification_entry_needs_a_commit_and_an_artefact(self):
        docs = valid_docs()
        docs["PROJECT_STATUS.md"] = valid_project_status(
            verification=["- **Verification:** it works, honest"]
        )
        self.write_docs(docs)
        proc, payload = self.cli_json("validate")
        self.assertEqual(proc.returncode, 1)
        self.assertIn("status.verification.commit", self.codes(payload, "error"))
        self.assertIn("status.verification.evidence", self.codes(payload, "error"))

    def test_verification_evidence_path_must_exist(self):
        docs = valid_docs()
        docs["PROJECT_STATUS.md"] = valid_project_status(
            verification=[
                "- **Verification:** commit `%s` — checked — evidence `docs/absent.json`" % ("a" * 40)
            ]
        )
        self.write_docs(docs)
        proc, payload = self.cli_json("validate")
        self.assertEqual(proc.returncode, 1)
        self.assertIn("status.verification.evidence_missing", self.codes(payload, "error"))

    def test_verification_commit_must_exist_in_the_repository(self):
        docs = valid_docs()
        docs["PROJECT_STATUS.md"] = valid_project_status(
            verification=[
                "- **Verification:** commit `deadbeefdeadbeefdeadbeefdeadbeefdeadbeef` — checked — "
                "evidence `README.md`"
            ]
        )
        self.write_docs(docs)
        (self.repo / "README.md").write_text("fixture\n", encoding="utf-8")
        proc, payload = self.cli_json("check")
        self.assertEqual(proc.returncode, 1)
        self.assertIn("status.verification_commit_unknown", self.codes(payload, "error"))


class FilesystemSafetyTests(RepoCase):
    """P2: nested repositories, worktrees, symlinks, and write boundaries."""

    def test_symlinked_document_is_not_replaced(self):
        self.write_docs()
        self.commit_all("docs: fixture")
        target = self.repo / "PROJECT_STATUS.md"
        real = self.repo / "real-status.md"
        original = target.read_text(encoding="utf-8")
        real.write_text(original, encoding="utf-8")
        target.unlink()
        os.symlink("real-status.md", str(target))

        proc = self.cli("update")
        self.assertEqual(proc.returncode, 4)
        self.assertIn("symbolic link", proc.stderr.lower())
        self.assertTrue(os.path.islink(str(target)), "the link must survive")
        self.assertEqual(real.read_text(encoding="utf-8"), original)

    def test_symlinked_document_blocks_init(self):
        real = self.repo / "elsewhere.md"
        real.write_text("# Project Status\n", encoding="utf-8")
        os.symlink(str(real), str(self.repo / "PROJECT_STATUS.md"))

        proc = self.cli("init")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertTrue(os.path.islink(str(self.repo / "PROJECT_STATUS.md")))
        self.assertEqual(real.read_text(encoding="utf-8"), "# Project Status\n")

    def test_documents_symlinked_into_another_directory_are_not_written_through(self):
        outside = Path(self._tmp) / "outside"
        outside.mkdir()
        content = valid_project_status()
        (outside / "status.md").write_text(content, encoding="utf-8")
        os.symlink(str(outside / "status.md"), str(self.repo / "PROJECT_STATUS.md"))
        proc = self.cli("update")
        self.assertEqual(proc.returncode, 4)
        self.assertEqual((outside / "status.md").read_text(encoding="utf-8"), content)

    def test_guard_rejects_a_target_outside_the_project(self):
        prodoc = load_prodoc()
        outside = Path(self._tmp) / "elsewhere"
        outside.mkdir()
        with self.assertRaises(prodoc.ProdocError) as caught:
            prodoc.guard_write_target(outside / "PROJECT_STATUS.md", self.repo)
        self.assertEqual(caught.exception.exit_code, 4)

    def test_guard_allows_a_normal_target(self):
        prodoc = load_prodoc()
        allowed = prodoc.guard_write_target(self.repo / "PROJECT_STATUS.md", self.repo)
        self.assertEqual(allowed, self.repo / "PROJECT_STATUS.md")

    def test_nested_repository_is_not_reached_into(self):
        """An inner repository must not read or write the outer project's docs."""
        self.write_docs()
        self.commit_all("docs: outer fixture")
        outer_before = self.read("PROJECT_STATUS.md")
        inner = self.repo / "vendor" / "inner"
        inner.mkdir(parents=True)
        self.git_in(inner, "init", "-q")
        self.git_in(inner, "config", "user.email", "t@e.invalid")
        self.git_in(inner, "config", "user.name", "T")

        proc, payload = self.cli_json("status", cwd=inner)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(payload["info"]["repo"], str(inner))
        self.assertNotIn("repo.worktree_root", self.codes(payload, "info"))
        self.assertFalse(payload["info"]["documents"]["PROJECT_STATUS.md"]["present"])

        proc = self.cli("init", cwd=inner)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        for doc in CANONICAL_DOCS:
            self.assertTrue((inner / doc).is_file(), doc)
        self.assertEqual(self.read("PROJECT_STATUS.md"), outer_before, "outer docs must be untouched")

    def test_linked_worktree_is_used_without_touching_the_main_checkout(self):
        self.write_docs()
        self.commit_all("docs: fixture")
        main_before = self.read("PROJECT_STATUS.md")
        worktree = Path(self._tmp) / "wt"
        self.git("worktree", "add", "-q", str(worktree), "-b", "wt-branch")

        proc, payload = self.cli_json("status", cwd=worktree)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(payload["info"]["repo"], str(worktree))
        self.assertFalse(payload["info"]["git"]["detached"])

        proc = self.cli("update", cwd=worktree)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("wt-branch", (worktree / "PROJECT_STATUS.md").read_text(encoding="utf-8"))
        self.assertEqual(self.read("PROJECT_STATUS.md"), main_before, "main checkout must be untouched")

    def test_commands_do_not_create_files_outside_the_project(self):
        outside = Path(self._tmp) / "watch"
        outside.mkdir()
        (outside / "marker").write_text("x", encoding="utf-8")
        before = sorted(str(p.relative_to(outside)) for p in outside.rglob("*"))

        self.write_docs()
        for args in (("init",), ("validate",), ("status",), ("check",), ("update",), ("update", "--dry-run")):
            self.cli(*args)
        after = sorted(str(p.relative_to(outside)) for p in outside.rglob("*"))
        self.assertEqual(before, after)

    def test_repo_flag_elsewhere_does_not_write_into_the_cwd(self):
        elsewhere = Path(self._tmp) / "target"
        elsewhere.mkdir()
        self.git_in(elsewhere, "init", "-q")
        self.assertEqual(self.cli("init", "--repo", str(elsewhere)).returncode, 0)
        for doc in CANONICAL_DOCS:
            self.assertTrue((elsewhere / doc).is_file(), doc)
            self.assertFalse((self.repo / doc).exists(), doc)

    def test_shallow_clone_does_not_accuse_truncated_history(self):
        """CI checkouts are shallow. An absent commit is unconfirmed, not wrong.

        Regression for the first real CI run, where `prodoc check` failed on a
        default `actions/checkout` clone because a cited commit was simply not
        fetched.
        """
        (self.repo / "README.md").write_text("fixture\n", encoding="utf-8")
        old_sha = self.commit_all("chore: first")
        docs = valid_docs()
        docs["PROJECT_STATUS.md"] = valid_project_status(
            verification=[
                "- **Verification:** commit `%s` — earlier run — evidence `README.md`" % old_sha
            ]
        )
        self.write_docs(docs)
        self.commit_all("docs: cite an earlier commit")

        shallow = Path(self._tmp) / "shallow"
        run_git(["clone", "-q", "--depth", "1", self.repo.as_uri(), str(shallow)],
                Path(self._tmp), self.env)
        self.assertTrue(
            run_git(["rev-parse", "--is-shallow-repository"], shallow, self.env).stdout.strip() == "true"
        )

        proc, payload = self.cli_json("check", cwd=shallow)
        self.assertEqual(proc.returncode, 0, payload)
        self.assertNotIn("status.verification_commit_unknown", self.codes(payload, "error"))
        self.assertIn("git.shallow", self.codes(payload, "info"))
        self.assertIn("status.verification_commit_unavailable", self.codes(payload, "warning"))

    def test_full_clone_still_rejects_a_genuinely_unknown_commit(self):
        """The shallow allowance must not weaken the check on full history."""
        docs = valid_docs()
        docs["PROJECT_STATUS.md"] = valid_project_status(
            verification=[
                "- **Verification:** commit `deadbeefdeadbeefdeadbeefdeadbeefdeadbeef` — claimed — "
                "evidence `README.md`"
            ]
        )
        self.write_docs(docs)
        (self.repo / "README.md").write_text("fixture\n", encoding="utf-8")
        proc, payload = self.cli_json("check")
        self.assertEqual(proc.returncode, 1)
        self.assertIn("status.verification_commit_unknown", self.codes(payload, "error"))

    def test_concurrent_change_between_checks_is_refused(self):
        """The pre-replace re-check must catch a change made during the write.

        `os.fsync` runs after the temporary file is written and before the second
        hash check, so interposing on it lands a concurrent write exactly inside
        the window the re-check exists to close.
        """
        prodoc = load_prodoc()
        target = self.repo / "PROJECT_STATUS.md"
        target.write_text("original\n", encoding="utf-8")
        expected = prodoc.sha256_text("original\n")

        real_fsync = os.fsync
        calls = {"n": 0}

        def interposing_fsync(fd):
            calls["n"] += 1
            target.write_text("sneaked in\n", encoding="utf-8")
            return real_fsync(fd)

        os.fsync = interposing_fsync
        try:
            with self.assertRaises(prodoc.ProdocError) as caught:
                prodoc.write_atomic(target, "ours\n", expected_sha=expected)
        finally:
            os.fsync = real_fsync
        self.assertEqual(caught.exception.exit_code, 4)
        self.assertEqual(calls["n"], 1, "the concurrent write landed inside the window")
        self.assertEqual(target.read_text(encoding="utf-8"), "sneaked in\n")
        leftovers = [p.name for p in self.repo.iterdir() if p.name.startswith(".prodoc-")]
        self.assertEqual(leftovers, [], "the temporary file must be cleaned up")

    def test_write_is_atomic_and_leaves_no_temporary_file(self):
        prodoc = load_prodoc()
        target = self.repo / "PROJECT_STATUS.md"
        target.write_text("original\n", encoding="utf-8")
        prodoc.write_atomic(target, "replacement\n", expected_sha=prodoc.sha256_text("original\n"))
        self.assertEqual(target.read_text(encoding="utf-8"), "replacement\n")
        leftovers = [p.name for p in self.repo.iterdir() if p.name.startswith(".prodoc-")]
        self.assertEqual(leftovers, [])


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

    def test_commands_run_from_a_subdirectory_find_the_documents(self):
        self.write_docs()
        self.commit_all("docs: fixture")
        subdir = self.repo / "src" / "deep"
        subdir.mkdir(parents=True)
        for command in ("status", "validate", "check"):
            proc, payload = self.cli_json(command, cwd=subdir)
            self.assertEqual(proc.returncode, 0, "%s from subdir: %s" % (command, payload))
            self.assertEqual(payload["info"]["repo"], str(self.repo))
            self.assertIn("repo.worktree_root", self.codes(payload, "info"))

    def test_init_from_a_subdirectory_writes_where_asked(self):
        subdir = self.repo / "src"
        subdir.mkdir()
        proc = self.cli("init", cwd=subdir)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        for doc in CANONICAL_DOCS:
            self.assertTrue((subdir / doc).is_file(), doc)
            self.assertFalse((self.repo / doc).exists(), doc)

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
        self.assertEqual(payload["info"]["observed"]["observed branch"], "-")


if __name__ == "__main__":
    unittest.main()
